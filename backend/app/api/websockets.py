import asyncio
import json
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.agents.events import register_ws_broadcaster, unregister_ws_broadcaster

router = APIRouter()

class ConnectionManager:
    """
    Manages WebSocket connections per task_id for streaming real-time agent events.
    """
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.loop = None

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)

        # Register callback for agent event broadcasting
        def sync_broadcaster_callback(event_data: dict):
            try:
                # Schedule async broadcast on current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.broadcast_to_task(task_id, event_data))
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
    Connects React frontend and streams real-time JSON events as agents execute.
    Includes heartbeat handling to maintain active connection.
    """
    await manager.connect(websocket, task_id)
    try:
        # Initial connection acknowledgement payload
        await websocket.send_json({
            "task_id": task_id,
            "event_type": "CONNECTION_ESTABLISHED",
            "agent": "System",
            "payload": {"message": f"Connected to live event stream for task {task_id}"},
            "timestamp": asyncio.get_event_loop().time()
        })
        
        while True:
            # Keep connection alive; client can send ping or text
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, task_id)
    except Exception as e:
        manager.disconnect(websocket, task_id)
