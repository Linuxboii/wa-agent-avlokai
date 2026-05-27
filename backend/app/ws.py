import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .auth import agent_from_token

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, event: str, data: dict) -> None:
        dead = []
        msg = json.dumps({"event": event, "data": data}, default=str)
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    # First frame must be {"type":"auth","token":"<jwt>"}. Token never in URL.
    try:
        first = await ws.receive_text()
        payload = json.loads(first)
        token = payload.get("token") if payload.get("type") == "auth" else None
    except Exception:
        await ws.close(code=4400)
        return
    if not token or not agent_from_token(token):
        await ws.close(code=4401)
        return
    manager.active.append(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive; ignore client payloads
    except WebSocketDisconnect:
        manager.disconnect(ws)
