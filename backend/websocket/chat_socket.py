"""WebSocket chat endpoint — supports streaming responses."""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}
        self._sids: Set[str] = set()

    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self._connections[session_id] = websocket
        self._sids.add(session_id)

    def disconnect(self, session_id: str) -> None:
        self._connections.pop(session_id, None)
        self._sids.discard(session_id)

    async def send_json(self, session_id: str, data: Dict[str, Any]) -> None:
        ws = self._connections.get(session_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(session_id)

    def is_connected(self, session_id: str) -> bool:
        return session_id in self._connections


manager = ConnectionManager()


@router.websocket("/chat/ws")
async def chat_websocket(
    websocket: WebSocket,
    session_id: str = Query(default=""),
):
    sid = session_id or str(uuid.uuid4())[:8]
    await manager.connect(websocket, sid)

    await manager.send_json(sid, {
        "type": "connected",
        "session_id": sid,
        "timestamp": time.time(),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "ping")

            if msg_type == "ping":
                await manager.send_json(sid, {
                    "type": "pong",
                    "session_id": sid,
                    "timestamp": time.time(),
                })
            elif msg_type == "message":
                msg = data.get("message", "")
                await manager.send_json(sid, {
                    "type": "processing",
                    "session_id": sid,
                    "timestamp": time.time(),
                })

                await asyncio.sleep(0.1)

                words = msg.split()
                buffer = ""
                for i, word in enumerate(words):
                    buffer += word + " "
                    if (i + 1) % 3 == 0 or i == len(words) - 1:
                        await manager.send_json(sid, {
                            "type": "chunk",
                            "content": buffer,
                            "session_id": sid,
                            "timestamp": time.time(),
                        })
                        buffer = ""
                        await asyncio.sleep(0.05)

                await manager.send_json(sid, {
                    "type": "complete",
                    "session_id": sid,
                    "timestamp": time.time(),
                    "metadata": {"processed": True},
                })

    except WebSocketDisconnect:
        manager.disconnect(sid)
    except Exception as exc:
        try:
            await manager.send_json(sid, {
                "type": "error",
                "detail": str(exc)[:300],
                "session_id": sid,
            })
        except Exception:
            pass
        manager.disconnect(sid)
