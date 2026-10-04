"""WebSocket Connection Hub for Real-time push updates to Next.js frontend."""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from app.core.logger import get_logger

log = get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket client connections for real-time dispatch."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info("WebSocket client connected. Total active: %d", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info("WebSocket client disconnected. Total active: %d", len(self.active_connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast payload to all connected frontend clients."""
        if not self.active_connections:
            return

        text_data = json.dumps(message, default=str)
        dead_connections: list[WebSocket] = []

        for conn in self.active_connections:
            try:
                await conn.send_text(text_data)
            except Exception:
                dead_connections.append(conn)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = ConnectionManager()
