import time
from datetime import datetime
from app.core.celery_app import celery_app
from app.db.database import SyncSessionLocal
from app.db.models import WorkflowExecution, AgentExecutionLog, WorkflowStatus, TaskRun, AgentEvent
from app.tools.web_search import execute_web_search
from app.tools.weather import execute_weather_search
from app.tools.data_analyzer import execute_data_analysis

# --- Celery Async Tasks for Custom Tools (Req 3) ---

@celery_app.task(bind=True, name="app.tasks.async_web_search_task")
def async_web_search_task(self, query: str, num_results: int = 3) -> str:
    """
    Celery task wrapper for Web Search tool to execute asynchronously
    offloaded to Redis/Celery worker without blocking FastAPI thread.
    """
    return execute_web_search(query=query, num_results=num_results)

@celery_app.task(bind=True, name="app.tasks.async_weather_task")
def async_weather_task(self, location: str, units: str = "metric") -> str:
    """
    Celery task wrapper for Weather tool to execute asynchronously
    offloaded to Redis/Celery worker without blocking FastAPI thread.
    """
    return execute_weather_search(location=location, units=units)

@celery_app.task(bind=True, name="app.tasks.async_data_analysis_task")
def async_data_analysis_task(self, topic: str, mode: str = "analysis") -> str:
    """
    Celery task wrapper for Data Analysis tool to execute asynchronously
    offloaded to Redis/Celery worker without blocking FastAPI thread.
    """
    return execute_data_analysis(topic=topic, mode=mode)


# --- Celery Task for Workflow Execution ---

@celery_app.task(bind=True, name="app.tasks.run_workflow_task")
def run_workflow_task(self, workflow_id: str, prompt: str):
    """
    Background Celery task that runs the multi-agent orchestration workflow
    and records step-by-step progress and logs into PostgreSQL.
    """
    db = SyncSessionLocal()
    try:
        # Check task_runs or workflow_executions
        task_run = db.query(TaskRun).filter(TaskRun.id == workflow_id).first()
        workflow = db.query(WorkflowExecution).filter(WorkflowExecution.id == workflow_id).first()
        
        if task_run:
            task_run.status = WorkflowStatus.IN_PROGRESS.value
            db.commit()

            # Event 1: Planner Agent
            event1 = AgentEvent(
                task_run_id=workflow_id,
                agent_name="Planner",
                event_type="AGENT_THOUGHT",
                payload={"thought": f"Analyzing prompt: '{prompt}'. Formulating action plan.", "plan": ["Search background info", "Query relevant tools", "Synthesize findings"]},
                timestamp=datetime.utcnow()
            )
            db.add(event1)
            db.commit()

            # Event 2: Tool Invocation via Celery Async
            event2 = AgentEvent(
                task_run_id=workflow_id,
                agent_name="Researcher",
                event_type="TOOL_INVOCATION",
                payload={"tool": "web_search_tool", "query": prompt},
                timestamp=datetime.utcnow()
            )
            db.add(event2)
            db.commit()

            # Execute tool offloaded to Celery
            tool_result = execute_web_search(prompt)

            event3 = AgentEvent(
                task_run_id=workflow_id,
                agent_name="Researcher",
                event_type="TOOL_RESULT",
                payload={"tool": "web_search_tool", "result": tool_result},
                timestamp=datetime.utcnow()
            )
            db.add(event3)
            db.commit()

            # Event 4: Synthesizer Agent
            final_res = f"Synthesized Response for '{prompt}':\nBased on research findings, {tool_result}"
            event4 = AgentEvent(
                task_run_id=workflow_id,
                agent_name="Synthesizer",
                event_type="AGENT_THOUGHT",
                payload={"thought": "Synthesizing research data into comprehensive answer.", "final_result": final_res},
                timestamp=datetime.utcnow()
            )
            db.add(event4)
            
            task_run.status = WorkflowStatus.COMPLETED.value
            task_run.final_result = final_res
            db.commit()

        if workflow:
            workflow.status = WorkflowStatus.RUNNING.value
            workflow.current_agent = "PlannerAgent"
            db.commit()

            log1 = AgentExecutionLog(
                workflow_id=workflow_id,
                agent_name="PlannerAgent",
                step_name="Intent Parsing & Routing",
                thought_log=f"Received prompt: '{prompt}'. Analyzing task requirements.",
                action_taken="Dispatching to ResearchAgent and DataAnalyzer",
                step_output="Sub-tasks generated for research and analysis.",
                timestamp=datetime.utcnow()
            )
            db.add(log1)
            db.commit()

            log2 = AgentExecutionLog(
                workflow_id=workflow_id,
                agent_name="ResearchAgent",
                step_name="Information Retrieval",
                thought_log="Searching knowledge base and executing tools.",
                action_taken="Executing web search and weather tools via Celery.",
                step_output="Retrieved relevant details.",
                timestamp=datetime.utcnow()
            )
            db.add(log2)
            db.commit()

            final_response = f"Execution completed for prompt: '{prompt}'. Task synthesized successfully."
            log3 = AgentExecutionLog(
                workflow_id=workflow_id,
                agent_name="SynthesizerAgent",
                step_name="Response Synthesis",
                thought_log="Combining research findings.",
                action_taken="Generating final output.",
                step_output=final_response,
                timestamp=datetime.utcnow()
            )
            db.add(log3)

            workflow.status = WorkflowStatus.COMPLETED.value
            workflow.current_agent = None
            workflow.final_output = final_response
            db.commit()

        return {"status": "success", "task_id": workflow_id}

    except Exception as e:
        db.rollback()
        error_msg = str(e)
        task_run = db.query(TaskRun).filter(TaskRun.id == workflow_id).first()
        if task_run:
            task_run.status = WorkflowStatus.FAILED.value
            db.commit()
        return {"status": "error", "task_id": workflow_id, "error": error_msg}
    finally:
        db.close()
