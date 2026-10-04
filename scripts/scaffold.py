"""Phase-1 scaffolding helper: creates package markers and empty-dir placeholders.

Idempotent — existing files are never overwritten. Run from the repository root:

    python scripts/scaffold.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AI_PACKAGES: dict[str, str] = {
    "utils": "Cross-cutting helpers: structured logging, device selection, environment checks.",
    "video": "Video input abstraction: VideoSource, WebcamSource, FileSource, RTSPSource.",
    "detection": "Object detection (Ultralytics YOLO) producing typed Detection objects.",
    "tracking": "Multi-object tracking (ByteTrack / BoT-SORT) and per-track state management.",
    "activity": "Behaviour analysis on tracks: movement, loitering, crowd, abandoned objects, aggression.",
    "pose": "Pose estimation (YOLO-Pose), posture classification and temporal fall detection.",
    "zones": "Polygon zones (restricted areas etc.) and point-in-zone analysis.",
    "events": "Standardised Event objects, event engine with cooldowns, alert generation, evidence.",
    "risk": "Configurable behavioural risk scoring with human-readable explanations.",
    "privacy": "Privacy safeguards such as face blurring for stored evidence frames.",
    "publishing": "Publishing events and live state to Redis for the backend.",
    "pipeline": "Pipeline orchestration: per-camera workers, frame annotation, MJPEG output.",
}

BACKEND_PACKAGES: dict[str, str] = {
    "api": "FastAPI routers (cameras, zones, events, alerts, dashboard, health).",
    "core": "Cross-cutting concerns: logging, security, rate limiting, audit.",
    "models": "SQLAlchemy ORM models (database tables).",
    "schemas": "Pydantic request/response schemas (API contracts).",
    "services": "Business logic and the Redis event consumer.",
    "websocket": "WebSocket connection manager and /ws/events endpoint.",
    "database": "Async SQLAlchemy engine/session management.",
}

GITKEEP_DIRS: tuple[str, ...] = (
    "ai-engine/models",
    "ai-engine/tests",
    "backend/tests",
    "database/migrations",
    "database/init",
    "videos/sample",
    "evidence",
    "frontend",
)


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def main() -> None:
    created: list[Path] = []
    for base, packages in (("ai-engine/app", AI_PACKAGES), ("backend/app", BACKEND_PACKAGES)):
        for name, doc in packages.items():
            init = ROOT / base / name / "__init__.py"
            if write_if_missing(init, f'"""{doc}"""\n'):
                created.append(init)
    for rel in GITKEEP_DIRS:
        keep = ROOT / rel / ".gitkeep"
        if write_if_missing(keep, ""):
            created.append(keep)

    for path in created:
        print("created", path.relative_to(ROOT).as_posix())
    print(f"done - {len(created)} file(s) created")


if __name__ == "__main__":
    main()
