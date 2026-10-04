"""Behavioral scene analytics:
- Loitering detection (staying within radius for > duration)
- Crowd density counting & thresholds
- Abandoned object detection (unattended bag/backpack/suitcase)
- Aggressive / fighting activity heuristics (sudden rapid proximity & motion)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any

from app.config import get_settings
from app.detection.detector import Detection
from app.tracking.tracker import TrackState
from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class LoiteringState:
    anchor_center: tuple[float, float]
    anchor_time: float
    last_event_time: float = 0.0


class LoiteringDetector:
    """Detects when a tracked person remains within a bounding radius for longer than threshold."""

    def __init__(
        self,
        time_threshold_seconds: float | None = None,
        radius_pixels: float | None = None,
    ) -> None:
        settings = get_settings()
        self.time_threshold = time_threshold_seconds or settings.loitering_time_seconds
        self.radius = radius_pixels or settings.loitering_radius_pixels
        self._anchors: dict[int, LoiteringState] = {}

    def check(self, track: TrackState, current_time: float | None = None) -> float | None:
        """Check if track is loitering.

        Returns:
            Loitering duration (seconds) if threshold exceeded, else None.
        """
        now = current_time or time.time()
        tid = track.track_id
        center = track.center

        if tid not in self._anchors:
            self._anchors[tid] = LoiteringState(anchor_center=center, anchor_time=now)
            return None

        state = self._anchors[tid]
        dist = math.hypot(center[0] - state.anchor_center[0], center[1] - state.anchor_center[1])

        if dist > self.radius:
            # Person moved outside radius: reset anchor
            state.anchor_center = center
            state.anchor_time = now
            return None

        elapsed = now - state.anchor_time
        if elapsed >= self.time_threshold:
            return round(elapsed, 1)

        return None

    def cleanup(self, active_track_ids: set[int]) -> None:
        """Remove tracks no longer active."""
        expired = [tid for tid in self._anchors if tid not in active_track_ids]
        for tid in expired:
            del self._anchors[tid]


class CrowdDensityAnalyzer:
    """Monitors crowd size and categorizes density level."""

    def __init__(
        self,
        high_threshold: int | None = None,
        critical_threshold: int | None = None,
    ) -> None:
        settings = get_settings()
        self.high_thresh = high_threshold or settings.crowd_threshold
        self.critical_thresh = critical_threshold or settings.crowd_critical_threshold

    def evaluate(self, people_count: int) -> tuple[str, bool]:
        """Returns: (density_level: NORMAL|HIGH|CRITICAL, is_alert)"""
        if people_count >= self.critical_thresh:
            return "CRITICAL", True
        if people_count >= self.high_thresh:
            return "HIGH", True
        return "NORMAL", False


@dataclass
class StationaryObjectState:
    class_name: str
    bbox: list[float]
    first_seen: float
    last_seen: float


class AbandonedObjectDetector:
    """Monitors stationary luggage/items (backpack, handbag, suitcase) without an owner nearby."""

    TARGET_OBJECTS = {"backpack", "handbag", "suitcase"}

    def __init__(
        self,
        duration_seconds: float | None = None,
        owner_distance_px: float | None = None,
    ) -> None:
        settings = get_settings()
        self.duration = duration_seconds or settings.abandoned_object_seconds
        self.owner_distance = owner_distance_px or settings.abandoned_owner_distance_px
        self._tracked_objects: dict[str, StationaryObjectState] = {}

    def update(
        self,
        detections: list[Detection],
        person_tracks: list[TrackState],
        timestamp: float | None = None,
    ) -> list[dict[str, Any]]:
        """Identify items that have remained stationary without a nearby person.

        Returns:
            List of detected possible abandoned object events.
        """
        now = timestamp or time.time()
        abandoned_events: list[dict[str, Any]] = []

        item_detections = [d for d in detections if d.class_name in self.TARGET_OBJECTS]

        for item in item_detections:
            center = item.center
            # Check if any person is within owner distance
            has_nearby_person = False
            for p in person_tracks:
                if math.hypot(p.center[0] - center[0], p.center[1] - center[1]) <= self.owner_distance:
                    has_nearby_person = True
                    break

            # Key by rounded spatial coordinate grid (bucket ~ 50px)
            grid_key = f"{item.class_name}_{int(center[0] // 50)}_{int(center[1] // 50)}"

            if has_nearby_person:
                # Owner present, reset timer
                if grid_key in self._tracked_objects:
                    del self._tracked_objects[grid_key]
                continue

            if grid_key not in self._tracked_objects:
                self._tracked_objects[grid_key] = StationaryObjectState(
                    class_name=item.class_name,
                    bbox=item.bbox,
                    first_seen=now,
                    last_seen=now,
                )
            else:
                obj_state = self._tracked_objects[grid_key]
                obj_state.last_seen = now
                elapsed = now - obj_state.first_seen

                if elapsed >= self.duration:
                    abandoned_events.append({
                        "event_type": "possible_abandoned_object",
                        "object_class": item.class_name,
                        "duration": round(elapsed, 1),
                        "bbox": item.bbox,
                        "center": center,
                        "confidence": item.confidence,
                    })

        # Evict items not seen in this frame
        current_keys = {
            f"{item.class_name}_{int(item.center[0] // 50)}_{int(item.center[1] // 50)}"
            for item in item_detections
        }
        expired = [k for k in self._tracked_objects if k not in current_keys]
        for k in expired:
            del self._tracked_objects[k]

        return abandoned_events


class AggressiveActivityDetector:
    """Heuristic detector for possible aggressive or fighting-like interactions.

    Note:
    This is an initial motion/proximity heuristic. Safe City AI cleanly abstracts
    this module so future 3D-CNN / Video Action Recognition models can replace it.
    """

    def __init__(self, proximity_threshold_px: float = 80.0, speed_threshold_px: float = 120.0) -> None:
        self.prox_thresh = proximity_threshold_px
        self.speed_thresh = speed_threshold_px

    def check(self, tracks: list[TrackState]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        n = len(tracks)
        if n < 2:
            return events

        for i in range(n):
            for j in range(i + 1, n):
                t1, t2 = tracks[i], tracks[j]
                dist = math.hypot(t1.center[0] - t2.center[0], t1.center[1] - t2.center[1])

                # High proximity + both exhibiting rapid movement
                fast_motion = t1.pixel_velocity > self.speed_thresh and t2.pixel_velocity > self.speed_thresh
                if dist <= self.prox_thresh and fast_motion:
                    events.append({
                            "event_type": "possible_aggressive_activity",
                            "track_ids": [t1.track_id, t2.track_id],
                            "distance_px": round(dist, 1),
                            "confidence": 0.70,
                        })
        return events
