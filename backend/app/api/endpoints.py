import uuid
import asyncio
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.database import get_sync_db, SyncSessionLocal
from app.db.models import TaskRun, AgentEvent, WorkflowStatus
from app.agents.graph import run_agent_workflow
from app.tasks.tasks import run_workflow_task

router = APIRouter()

class TaskCreateRequest(BaseModel):
    """Payload schema for POST /api/tasks"""
    prompt: str = Field(description="The complex problem or instructions for the multi-agent system to solve.", min_length=1)

class TaskCreateResponse(BaseModel):
    """Response schema for POST /api/tasks"""
    task_id: str = Field(description="Unique UUID identifier for the created task.")
    status: str = Field(description="Initial status of the task run.")

class AgentEventSchema(BaseModel):
    id: str
    agent_name: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: Any

    class Config:
        from_attributes = True

class TaskDetailResponse(BaseModel):
    id: str
    prompt: str
    status: str
    final_result: Optional[str] = None
    created_at: Any
    updated_at: Any
    events: List[AgentEventSchema] = []

    class Config:
        from_attributes = True

def _background_workflow_runner(task_id: str, prompt: str):
    """Background execution runner invoking the LangGraph multi-agent state machine."""
    try:
        run_agent_workflow(task_id=task_id, prompt=prompt)
    except Exception as e:
        print(f"[Workflow Execution Error] {e}")

@router.post("/tasks", response_model=TaskCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_task(request: TaskCreateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_sync_db)):
    """
    POST /api/tasks
    Initiates a new multi-agent workflow run.
    Stores initial TaskRun record in PostgreSQL, dispatches the state machine asynchronously,
    and immediately returns the unique task_id.
    """
    task_id = str(uuid.uuid4())
    
    # Create TaskRun record in database
    task_run = TaskRun(
        id=task_id,
        prompt=request.prompt,
        status=WorkflowStatus.PENDING.value
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    # Dispatch workflow execution asynchronously in background thread
    background_tasks.add_task(_background_workflow_runner, task_id, request.prompt)
    
    # Also trigger Celery task worker for audit queue tracking
    try:
        run_workflow_task.delay(workflow_id=task_id, prompt=request.prompt)
    except Exception as e:
        print(f"[Celery Dispatch Notice] Running via direct background task ({e})")

    return TaskCreateResponse(task_id=task_id, status=WorkflowStatus.PENDING.value)

@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task_details(task_id: str, db: Session = Depends(get_sync_db)):
    """
    GET /api/tasks/{task_id}
    Retrieves task execution details, final output, and full sequence of logged agent events.
    """
    task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
    if not task_run:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")
    return task_run

@router.get("/tasks", response_model=List[TaskCreateResponse])
async def list_tasks(limit: int = 20, db: Session = Depends(get_sync_db)):
    """
    GET /api/tasks
    Lists recent task runs.
    """
    tasks = db.query(TaskRun).order_by(TaskRun.created_at.desc()).limit(limit).all()
    return [TaskCreateResponse(task_id=t.id, status=t.status) for t in tasks]
