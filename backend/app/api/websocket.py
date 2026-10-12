from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import logging

router = APIRouter(prefix="/ws", tags=["WebSocket"])
logger = logging.getLogger("codeguard.websocket")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"WebSocket send error: {e}")

manager = ConnectionManager()

@router.websocket("/pr/{pr_id}")
async def pr_websocket_endpoint(websocket: WebSocket, pr_id: int):
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps({
            "event": "connected",
            "pr_id": pr_id,
            "message": f"Connected to live updates for PR #{pr_id}"
        }))
        while True:
            data = await websocket.receive_text()
            # Echo or process incoming socket messages
            await websocket.send_text(json.dumps({
                "event": "message_ack",
                "received": data
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
