"""Standardized event models and Event Engine with cooldown suppression."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from app.config import get_settings
from app.privacy.blur import blur_faces_in_frame
from app.risk.engine import RiskEvaluation
from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class Event:
    """Standardized Safe City event record."""
    id: str
    camera_id: str
    event_type: str
    confidence: float
    risk_score: int
    risk_level: str
    timestamp: float = field(default_factory=time.time)
    track_id: int | None = None
    evidence_frame: str | None = None  # relative filename or URL
    reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "camera_id": self.camera_id,
            "event_type": self.event_type,
            "confidence": round(self.confidence, 3),
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp,
            "track_id": self.track_id,
            "evidence_frame": self.evidence_frame,
            "reasons": self.reasons,
            "metadata": self.metadata,
        }


class EventEngine:
    """Deduplicates events with cooldowns and saves evidence snapshots."""

    def __init__(self, cooldown_seconds: float | None = None) -> None:
        settings = get_settings()
        self.cooldown = cooldown_seconds if cooldown_seconds is not None else settings.event_cooldown_seconds
        self.evidence_dir = settings.evidence_path
        self.face_blur = settings.face_blur_enabled
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

        # (camera_id, event_type, track_id) -> last_triggered_timestamp
        self._cooldowns: dict[tuple[str, str, int | None], float] = {}

    def create_event(
        self,
        camera_id: str,
        event_type: str,
        confidence: float,
        risk: RiskEvaluation,
        track_id: int | None = None,
        frame: np.ndarray | None = None,
        head_bboxes: list[list[float]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event | None:
        """Create an event if outside cooldown period."""
        now = time.time()
        cd_key = (camera_id, event_type, track_id)

        if cd_key in self._cooldowns and (now - self._cooldowns[cd_key]) < self.cooldown:
            # Suppressed by cooldown
            return None

        self._cooldowns[cd_key] = now
        event_id = str(uuid.uuid4())

        evidence_filename: str | None = None
        if frame is not None and frame.size > 0:
            evidence_filename = f"{camera_id}_{event_type}_{int(now)}_{event_id[:8]}.jpg"
            full_path = self.evidence_dir / evidence_filename

            save_frame = frame
            if self.face_blur:
                save_frame = blur_faces_in_frame(frame, head_bboxes)

            cv2.imwrite(str(full_path), save_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

        event = Event(
            id=event_id,
            camera_id=camera_id,
            event_type=event_type,
            confidence=confidence,
            risk_score=risk.score,
            risk_level=risk.level,
            timestamp=now,
            track_id=track_id,
            evidence_frame=evidence_filename,
            reasons=risk.reasons,
            metadata=metadata or {},
        )

        log.info(
            "Event generated: %s (risk=%s, score=%d)",
            event_type,
            risk.level,
            risk.score,
            extra={
                "camera_id": camera_id,
                "track_id": track_id,
                "event": event_type,
                "severity": risk.level,
            },
        )
        return event
