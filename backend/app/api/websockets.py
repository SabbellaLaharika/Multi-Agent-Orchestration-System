import asyncio
import json
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.agents.events import register_ws_broadcaster, unregister_ws_broadcaster
from app.db.database import SyncSessionLocal
from app.db.models import AgentEvent

router = APIRouter()

class ConnectionManager:
    """
    Manages WebSocket connections per task_id for streaming real-time agent events.
    Thread-safe implementation that supports cross-thread event broadcasting.
    """
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if not self.main_loop:
            self.main_loop = asyncio.get_running_loop()

        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

        # Thread-safe callback for live agent event broadcasting across worker threads
        def sync_broadcaster_callback(event_data: dict):
            try:
                if self.main_loop and self.main_loop.is_running():
                    asyncio.run_coroutine_threadsafe(self.broadcast_to_task(task_id, event_data), self.main_loop)
            except Exception as e:
                print(f"[WS Broadcaster Error] {e}")

        register_ws_broadcaster(task_id, sync_broadcaster_callback)

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
                unregister_ws_broadcaster(task_id)

    async def broadcast_to_task(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            for conn in disconnected:
                self.disconnect(conn, task_id)

manager = ConnectionManager()

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint: WS /api/ws/{task_id}
    Connects React frontend, replays historical events from DB, and streams live events.
    """
    await manager.connect(websocket, task_id)
    try:
        # Send connection acknowledgement
        await websocket.send_json({
            "task_id": task_id,
            "event_type": "CONNECTION_ESTABLISHED",
            "agent": "System",
            "payload": {"message": f"Connected to live event stream for task {task_id}"},
            "timestamp": asyncio.get_event_loop().time()
        })

        # Replay past logged events from Postgres DB for instant timeline hydration
        db = SyncSessionLocal()
        try:
            past_events = db.query(AgentEvent).filter(AgentEvent.task_run_id == task_id).order_by(AgentEvent.timestamp.asc()).all()
            for event in past_events:
                await websocket.send_json({
                    "task_id": task_id,
                    "event_type": event.event_type,
                    "agent": event.agent_name,
                    "payload": event.payload,
                    "timestamp": event.timestamp.isoformat() + "Z"
                })
        except Exception as e:
            print(f"[WS Event Replay Error] {e}")
        finally:
            db.close()

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)
    except Exception as e:
        manager.disconnect(websocket, task_id)
