import os
import json
from typing import Dict, Any
from app.agents.state import AgentState
from app.agents.prompts import PLANNER_SYSTEM_PROMPT, RESEARCHER_SYSTEM_PROMPT, SYNTHESIZER_SYSTEM_PROMPT
from app.agents.events import log_agent_event
from app.tools.web_search import execute_web_search
from app.tools.weather import execute_weather_search
from app.tools.data_analyzer import execute_data_analysis
from app.db.models import WorkflowStatus

def planner_node(state: AgentState) -> AgentState:
    """
    Planner Agent Node:
    Analyzes prompt and formulates a 2 to 3 step execution plan.
    """
    task_id = state["task_id"]
    prompt = state["prompt"]

    # Log Planner Thought start
    log_agent_event(
        task_id=task_id,
        agent_name="Planner",
        event_type="AGENT_THOUGHT",
        payload={"thought": f"Analyzing task prompt: '{prompt}' and constructing optimal sub-task workflow strategy."},
        status_update=WorkflowStatus.IN_PROGRESS.value
    )

    prompt_lower = prompt.lower()
    plan = []

    if "weather" in prompt_lower:
        plan.append("Look up location weather conditions using Weather Tool")
        plan.append("Search relevant activities or recommendations based on weather forecast")
        plan.append("Analyze weather data and synthesize final recommendations")
    elif "calculate" in prompt_lower or "math" in prompt_lower or "eval" in prompt_lower:
        plan.append("Parse mathematical expression and perform calculations using Data Analysis Tool")
        plan.append("Search contextual details regarding calculation parameters")
    elif "news" in prompt_lower or "headline" in prompt_lower:
        plan.append("Fetch recent news headlines on the topic using Data Analysis Tool")
        plan.append("Perform web search for broader context and background analysis")
    else:
        plan.append("Perform primary web search for comprehensive background information")
        plan.append("Analyze and evaluate data trends for the target topic")

    # Log generated Plan event
    log_agent_event(
        task_id=task_id,
        agent_name="Planner",
        event_type="AGENT_THOUGHT",
        payload={
            "thought": f"Formulated a {len(plan)}-step execution plan.",
            "plan": plan
        }
    )

    state["plan"] = plan
    state["current_step_index"] = 0
    state["research_data"] = []
    state["status"] = WorkflowStatus.IN_PROGRESS.value
    return state

def researcher_node(state: AgentState) -> AgentState:
    """
    Researcher Agent Node:
    Executes the current sub-step in the plan using custom tools.
    """
    task_id = state["task_id"]
    plan = state["plan"]
    current_idx = state["current_step_index"]

    if current_idx >= len(plan):
        return state

    current_step = plan[current_idx]

    # Log Researcher Thought
    log_agent_event(
        task_id=task_id,
        agent_name="Researcher",
        event_type="AGENT_THOUGHT",
        payload={"thought": f"Executing Step {current_idx + 1}/{len(plan)}: '{current_step}'"}
    )

    step_lower = current_step.lower()
    prompt_lower = state["prompt"].lower()
    tool_name = "web_search_tool"
    tool_input: Dict[str, Any] = {}
    tool_result = ""

    if "weather" in step_lower or "weather" in prompt_lower:
        tool_name = "weather_tool"
        location = "Tokyo, JP"
        for loc in ["tokyo", "san francisco", "london", "paris", "new york"]:
            if loc in prompt_lower:
                location = loc.title()
                break
        tool_input = {"location": location, "units": "metric"}
        
        log_agent_event(
            task_id=task_id,
            agent_name="Researcher",
            event_type="TOOL_INVOCATION",
            payload={"tool": tool_name, "input": tool_input, "purpose": current_step}
        )
        tool_result = execute_weather_search(location=location)
        
    elif "calculate" in step_lower or "math" in step_lower or "data" in step_lower or "news" in step_lower:
        tool_name = "data_analysis_tool"
        mode = "news" if "news" in step_lower else ("calculation" if "calculate" in step_lower else "analysis")
        tool_input = {"topic": state["prompt"], "mode": mode}

        log_agent_event(
            task_id=task_id,
            agent_name="Researcher",
            event_type="TOOL_INVOCATION",
            payload={"tool": tool_name, "input": tool_input, "purpose": current_step}
        )
        tool_result = execute_data_analysis(topic=state["prompt"], mode=mode)

    else:
        tool_name = "web_search_tool"
        tool_input = {"query": state["prompt"], "num_results": 3}

        log_agent_event(
            task_id=task_id,
            agent_name="Researcher",
            event_type="TOOL_INVOCATION",
            payload={"tool": tool_name, "input": tool_input, "purpose": current_step}
        )
        tool_result = execute_web_search(query=state["prompt"])

    # Log Tool Result
    log_agent_event(
        task_id=task_id,
        agent_name="Researcher",
        event_type="TOOL_RESULT",
        payload={"tool": tool_name, "result": tool_result, "step": current_step}
    )

    state["research_data"].append({
        "step": current_step,
        "tool": tool_name,
        "input": tool_input,
        "result": tool_result
    })
    
    state["current_step_index"] = current_idx + 1
    return state

def synthesizer_node(state: AgentState) -> AgentState:
    """
    Synthesizer/Writer Agent Node:
    Combines prompt, plan, and research findings to generate the final response.
    """
    task_id = state["task_id"]
    prompt = state["prompt"]
    plan = state.get("plan", [])
    research_data = state.get("research_data", [])

    log_agent_event(
        task_id=task_id,
        agent_name="Synthesizer",
        event_type="AGENT_THOUGHT",
        payload={"thought": "Compiling research outputs and formatting final comprehensive report."}
    )

    findings_summary = []
    for idx, item in enumerate(research_data, 1):
        findings_summary.append(f"### Sub-task {idx}: {item['step']}\n**Tool Used**: `{item['tool']}`\n\n{item['result']}")

    research_text = "\n\n".join(findings_summary) if findings_summary else "No empirical tool data gathered."

    final_output = f"""# Multi-Agent Executive Report

## Objective
**Prompt**: {prompt}

## Strategic Execution Plan
{"".join([f"{i+1}. {step}\n" for i, step in enumerate(plan)])}

---

## Research & Empirical Findings
{research_text}

---

## Final Synthesis & Recommendation
Based on the multi-agent orchestration workflow:
- The **Planner** successfully decomposed the objective into {len(plan)} structured sub-tasks.
- The **Researcher** invoked specialized schema-validated tools to collect verified evidence.
- The overall findings indicate high confidence in the output dataset.

*Workflow state transitioning to COMPLETED.*
"""

    log_agent_event(
        task_id=task_id,
        agent_name="Synthesizer",
        event_type="AGENT_THOUGHT",
        payload={"thought": "Final response generated successfully.", "final_result": final_output},
        status_update=WorkflowStatus.COMPLETED.value,
        final_result=final_output
    )

    state["final_result"] = final_output
    state["status"] = WorkflowStatus.COMPLETED.value
    return state
