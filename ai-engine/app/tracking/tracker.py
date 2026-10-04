"""Object tracking and track state management for Safe City AI.

Supports:
- ByteTrack (default, fast & reliable)
- BoT-SORT (optional)
- TrackState maintaining temporal history, velocity, dwell time, activity label, zone membership
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from ultralytics import YOLO

from app.config import get_settings
from app.utils.device import resolve_device
from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class TrackPoint:
    timestamp: float
    center: tuple[float, float]
    bbox: list[float]


@dataclass
class TrackState:
    """Maintains rich temporal history for a tracked entity."""
    track_id: int
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    current_zone: str = "public_area"
    activity_state: str = "stationary"  # stationary | walking | running | falling
    history: deque[TrackPoint] = field(default_factory=lambda: deque(maxlen=90))

    # Computed kinematics
    pixel_velocity: float = 0.0  # px/s
    displacement: float = 0.0    # px total from anchor
    stationary_duration: float = 0.0  # seconds continuously stationary
    movement_duration: float = 0.0    # seconds continuously moving
    posture: str = "standing"         # standing | sitting | lying (from pose if available)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2.0, (self.bbox[1] + self.bbox[3]) / 2.0)

    @property
    def bottom_center(self) -> tuple[float, float]:
        return ((self.bbox[0] + self.bbox[2]) / 2.0, self.bbox[3])

    @property
    def total_dwell_seconds(self) -> float:
        return max(0.0, self.last_seen - self.first_seen)

    def update(self, bbox: list[float], confidence: float, timestamp: float | None = None) -> None:
        now = timestamp or time.time()
        self.last_seen = now
        self.bbox = bbox
        self.confidence = confidence
        self.history.append(TrackPoint(timestamp=now, center=self.center, bbox=bbox))

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "class_id": self.class_id,
            "class": self.class_name,
            "confidence": round(float(self.confidence), 3),
            "bbox": [round(float(c), 1) for c in self.bbox],
            "center": [round(c, 1) for c in self.center],
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "current_zone": self.current_zone,
            "activity": self.activity_state,
            "pixel_velocity": round(self.pixel_velocity, 1),
            "dwell_seconds": round(self.total_dwell_seconds, 1),
        }


class Tracker:
    """Ultralytics tracker wrapper (ByteTrack / BoT-SORT) with TrackState management."""

    def __init__(
        self,
        tracker_type: str | None = None,
        model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        settings = get_settings()
        self.tracker_type = tracker_type or settings.tracker_type
        self.model_name = model_name or settings.yolo_model
        self.device = resolve_device(device or settings.device)
        self.conf_threshold = settings.confidence_threshold
        self.iou_threshold = settings.iou_threshold
        self.imgsz = settings.inference_image_size
        self.target_classes = set(settings.detection_classes)
        self.history_len = settings.track_history_size
        self.lost_timeout = settings.track_lost_timeout_seconds

        weights_path = settings.model_file(self.model_name)
        log.info("Initializing tracker (%s) with model %s on %s", self.tracker_type, weights_path.name, self.device)
        self.model = YOLO(str(weights_path))

        raw_names = self.model.names
        self.class_names: dict[int, str] = raw_names if isinstance(raw_names, dict) else dict(enumerate(raw_names))
        self.allowed_class_ids = [
            cid for cid, cname in self.class_names.items() if cname in self.target_classes
        ]

        self.tracks: dict[int, TrackState] = {}
        self.tracker_cfg = f"{self.tracker_type}.yaml"

    def track(self, frame: np.ndarray, timestamp: float | None = None) -> list[TrackState]:
        """Process a frame with Ultralytics tracker, updating persistent TrackState objects.

        Returns:
            Active TrackState objects in this frame.
        """
        now = timestamp or time.time()
        if frame is None or frame.size == 0:
            self._cleanup_lost_tracks(now)
            return []

        results = self.model.track(
            source=frame,
            persist=True,
            tracker=self.tracker_cfg,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            classes=self.allowed_class_ids,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False,
        )

        active_this_frame: list[TrackState] = []
        if not results:
            self._cleanup_lost_tracks(now)
            return active_this_frame

        r = results[0]
        boxes = r.boxes
        if boxes is None or len(boxes) == 0:
            self._cleanup_lost_tracks(now)
            return active_this_frame

        xyxy_arr = boxes.xyxy.cpu().numpy()
        conf_arr = boxes.conf.cpu().numpy()
        cls_arr = boxes.cls.cpu().numpy()
        id_arr = boxes.id.cpu().numpy() if boxes.id is not None else None

        if id_arr is None:
            # Tracker didn't assign IDs yet (e.g. single unconfirmed frame)
            self._cleanup_lost_tracks(now)
            return active_this_frame

        for xyxy, conf, cid_raw, tid_raw in zip(xyxy_arr, conf_arr, cls_arr, id_arr, strict=False):
            tid = int(tid_raw)
            cid = int(cid_raw)
            cname = self.class_names.get(cid, "unknown")
            bbox = [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])]

            if tid in self.tracks:
                state = self.tracks[tid]
                state.update(bbox, float(conf), now)
            else:
                state = TrackState(
                    track_id=tid,
                    class_id=cid,
                    class_name=cname,
                    confidence=float(conf),
                    bbox=bbox,
                    first_seen=now,
                    last_seen=now,
                    history=deque(maxlen=self.history_len),
                )
                state.history.append(TrackPoint(timestamp=now, center=state.center, bbox=bbox))
                self.tracks[tid] = state

            active_this_frame.append(state)

        self._cleanup_lost_tracks(now)
        return active_this_frame

    def _cleanup_lost_tracks(self, current_time: float) -> None:
        """Evict tracks that haven't been seen for longer than TRACK_LOST_TIMEOUT_SECONDS."""
        expired_ids = [
            tid for tid, state in self.tracks.items()
            if (current_time - state.last_seen) > self.lost_timeout
        ]
        for tid in expired_ids:
            del self.tracks[tid]
