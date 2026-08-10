import json
from datetime import datetime
from typing import Dict, Any, Optional
from app.db.database import SyncSessionLocal
from app.db.models import AgentEvent, TaskRun, WorkflowStatus

# Global event broadcast listeners for WebSocket connections
_ws_broadcasters = {}

def register_ws_broadcaster(task_id: str, callback):
    """Register an active WebSocket broadcast callback for a task_id."""
    _ws_broadcasters[task_id] = callback

def unregister_ws_broadcaster(task_id: str):
    """Unregister WebSocket broadcast callback for task_id."""
    _ws_broadcasters.pop(task_id, None)

def log_agent_event(
    task_id: str,
    agent_name: str,
    event_type: str,
    payload: Dict[str, Any],
    status_update: Optional[str] = None,
    final_result: Optional[str] = None
):
    """
    Persists an agent event to PostgreSQL and streams it to active WebSockets.
    """
    timestamp_str = datetime.utcnow().isoformat() + "Z"
    
    # 1. DB Persistence
    db = SyncSessionLocal()
    try:
        event = AgentEvent(
            task_run_id=task_id,
            agent_name=agent_name,
            event_type=event_type,
            payload=payload,
            timestamp=datetime.utcnow()
        )
        db.add(event)
        
        task_run = db.query(TaskRun).filter(TaskRun.id == task_id).first()
        if task_run:
            if status_update:
                task_run.status = status_update
            if final_result:
                task_run.final_result = final_result
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Event Log DB Error] {e}")
    finally:
        db.close()

    # 2. WebSocket Streaming Broadcast
    event_data = {
        "task_id": task_id,
        "event_type": event_type,
        "agent": agent_name,
        "payload": payload,
        "timestamp": timestamp_str,
        "status": status_update,
        "final_result": final_result
    }
    
    broadcaster = _ws_broadcasters.get(task_id)
    if broadcaster:
        try:
            broadcaster(event_data)
        except Exception as e:
            print(f"[Event Log WS Error] {e}")

    return event_data
