"""AI Engine Central Service:
- REST API on port 8001
- Live MJPEG video stream with bounding boxes, track IDs, activity & zones (/stream/{camera_id})
- Dynamic camera worker management (start/stop)
- Background Event & Live State Publisher pushing events to Backend API and Redis
"""

from __future__ import annotations

import threading
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import cv2
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.events.engine import Event
from app.pipeline.pipeline import AIPipeline
from app.utils.logger import get_logger, setup_logging
from app.video.source import FileSource, VideoSource, WebcamSource

setup_logging()
log = get_logger("ai_service")
settings = get_settings()


class CameraWorker(threading.Thread):
    """Dedicated background thread for ingesting and analyzing one camera feed."""

    def __init__(self, camera_id: str, source: VideoSource) -> None:
        super().__init__(daemon=True, name=f"Worker-{camera_id}")
        self.camera_id = camera_id
        self.source = source
        self.pipeline = AIPipeline(camera_id=camera_id)
        self.running = False
        self.latest_jpeg: bytes | None = None
        self.latest_people_count: int = 0
        self.latest_fps: float = 0.0
        self.latest_events: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def run(self) -> None:
        log.info("Starting camera worker thread for %s", self.camera_id)
        if not self.source.open():
            log.error("Failed to open source for camera worker %s", self.camera_id)
            return

        meta = self.source.metadata
        self.pipeline.add_demo_restricted_zone(meta.width, meta.height)
        self.running = True

        target_interval = settings.min_frame_interval
        last_time = 0.0

        backend_url = f"{settings.api_url}/api/events"

        while self.running:
            ok, frame = self.source.read()
            if not ok or frame is None:
                time.sleep(0.05)
                continue

            now = time.time()
            if target_interval > 0 and (now - last_time) < target_interval:
                time.sleep(0.005)
                continue

            last_time = now
            result = self.pipeline.process_frame(frame, timestamp=now)

            encode_params = [cv2.IMWRITE_JPEG_QUALITY, settings.stream_jpeg_quality]
            ret, buf = cv2.imencode(".jpg", result.annotated_frame, encode_params)
            if ret:
                with self._lock:
                    self.latest_jpeg = buf.tobytes()
                    self.latest_people_count = result.people_count
                    self.latest_fps = result.fps
                    self.latest_events = [e.to_dict() for e in result.events]

            # If new events were generated, forward to Backend API asynchronously
            if result.events:
                for ev in result.events:
                    self._dispatch_event(backend_url, ev)

        self.source.release()
        log.info("Camera worker thread for %s stopped", self.camera_id)

    def _dispatch_event(self, url: str, ev: Event) -> None:
        def _send() -> None:
            try:
                payload = {
                    "camera_id": ev.camera_id,
                    "event_type": ev.event_type,
                    "confidence": ev.confidence,
                    "risk_score": ev.risk_score,
                    "risk_level": ev.risk_level,
                    "track_id": ev.track_id,
                    "evidence_frame": ev.evidence_frame,
                    "reasons": ev.reasons,
                    "metadata": ev.metadata,
                }
                httpx.post(url, json=payload, timeout=2.0)
            except Exception as e:
                log.debug("Event dispatch failed (backend might be offline): %s", e)

        threading.Thread(target=_send, daemon=True).start()

    def stop(self) -> None:
        self.running = False


class WorkerRegistry:
    def __init__(self) -> None:
        self.workers: dict[str, CameraWorker] = {}

    def get_or_create(self, camera_id: str) -> CameraWorker:
        if camera_id in self.workers and self.workers[camera_id].is_alive():
            return self.workers[camera_id]

        # Use Webcam if configured, otherwise fallback to sample File source if exists
        if settings.use_webcam:
            source = WebcamSource(camera_index=settings.webcam_index, camera_id=camera_id)
        else:
            source_file = settings.resolve_path("videos/sample/test.mp4")
            if source_file.exists():
                source = FileSource(file_path=source_file, camera_id=camera_id)
            else:
                source = WebcamSource(camera_index=settings.webcam_index, camera_id=camera_id)

        worker = CameraWorker(camera_id=camera_id, source=source)
        worker.start()
        self.workers[camera_id] = worker
        return worker

    def stop_all(self) -> None:
        for w in self.workers.values():
            w.stop()


registry = WorkerRegistry()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("AI Engine service starting on port %d...", settings.ai_engine_port)
    # Automatically spawn default camera worker
    registry.get_or_create(settings.default_camera_id)
    yield
    registry.stop_all()
    log.info("AI Engine service shutdown.")


app = FastAPI(
    title="Safe City AI - AI Engine Service",
    description="Vision Inference & MJPEG Streaming Service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "ai-engine",
        "device": settings.device,
        "workers": list(registry.workers.keys()),
    }


@app.get("/cameras/{camera_id}/stats")
def camera_stats(camera_id: str) -> dict[str, Any]:
    if camera_id not in registry.workers:
        raise HTTPException(status_code=404, detail="Camera worker not found")
    worker = registry.workers[camera_id]
    with worker._lock:
        return {
            "camera_id": camera_id,
            "people_count": worker.latest_people_count,
            "fps": round(worker.latest_fps, 1),
            "recent_events": worker.latest_events,
        }


@app.get("/stream/{camera_id}")
def stream_camera(camera_id: str) -> StreamingResponse:
    """Streams multipart MJPEG video directly viewable in any <img> tag on web dashboard."""
    worker = registry.get_or_create(camera_id)

    def frame_generator():
        placeholder: bytes | None = None
        while True:
            with worker._lock:
                frame_bytes = worker.latest_jpeg
            if frame_bytes is None:
                if placeholder is None:
                    import numpy as np
                    img = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(img, "CONNECTING TO CAMERA...", (140, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 230, 115), 2)
                    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 60])
                    placeholder = buf.tobytes()
                frame_bytes = placeholder

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
            time.sleep(0.04)  # ~25 FPS delivery rate

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
