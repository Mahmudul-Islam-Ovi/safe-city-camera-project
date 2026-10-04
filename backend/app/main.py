"""FastAPI Application entry point for Safe City AI Backend.

Includes:
- Lifespan initialization (database tables bootstrap)
- CORS middleware
- Static mounting for /evidence directory (evidence snapshots)
- REST API routers under /api
- WebSocket endpoint /ws/events
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.endpoints import router as api_router
from app.config import get_settings
from app.core.logger import get_logger, setup_logging
from app.database.session import init_db
from app.websocket.manager import ws_manager

setup_logging()
log = get_logger("backend_app")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("Starting Safe City Backend on port %d...", settings.backend_port)
    await init_db()
    yield
    log.info("Safe City Backend shutting down.")


app = FastAPI(
    title="Safe City AI - Surveillance & Behavioral Risk Analytics API",
    description="Privacy-conscious AI video analytics decision-support platform backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount evidence snapshots folder for dashboard review
evidence_path = settings.evidence_path
evidence_path.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=str(evidence_path)), name="evidence")

# Include API router
app.include_router(api_router, prefix=settings.api_prefix)


# WebSocket endpoint
@app.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        log.warning("WebSocket connection closed with error: %s", e)
        ws_manager.disconnect(websocket)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": "Safe City AI Backend",
        "status": "online",
        "docs": "/docs",
        "ws_endpoint": "/ws/events",
    }
