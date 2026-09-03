from typing import Dict, List, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        # Maps workspace_id to a list of active websocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, workspace_id: str):
        await websocket.accept()
        if workspace_id not in self.active_connections:
            self.active_connections[workspace_id] = []
        self.active_connections[workspace_id].append(websocket)
        logger.info(f"WebSocket connected for workspace: {workspace_id}")

    def disconnect(self, websocket: WebSocket, workspace_id: str):
        if workspace_id in self.active_connections:
            if websocket in self.active_connections[workspace_id]:
                self.active_connections[workspace_id].remove(websocket)
            if not self.active_connections[workspace_id]:
                del self.active_connections[workspace_id]
        logger.info(f"WebSocket disconnected for workspace: {workspace_id}")

    async def broadcast_to_workspace(self, workspace_id: str, message: Dict[str, Any]):
        if workspace_id in self.active_connections:
            # Serialize to JSON manually to avoid issues with UUIDs or datetimes not being serializable
            json_msg = json.dumps(message, default=str)
            for connection in self.active_connections[workspace_id]:
                try:
                    await connection.send_text(json_msg)
                except Exception as e:
                    logger.error(f"Error sending websocket message: {e}")

manager = ConnectionManager()

@router.websocket("/{workspace_id}")
async def websocket_endpoint(websocket: WebSocket, workspace_id: str):
    """
    Phase 8: Real-Time Updates WebSocket Endpoint
    Clients connect here to receive live events and incident notifications.
    """
    await manager.connect(websocket, workspace_id)
    try:
        while True:
            # We just keep the connection open and wait for a client ping or disconnect
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, workspace_id)
