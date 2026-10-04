"""Movement analysis for tracked entities.

Calculates:
- displacement
- direction (vector and compass)
- approximate pixel velocity (px/second)
- stationary duration & movement duration
- classification: stationary / walking / running

IMPORTANT LIMITATION:
This calculates PIXEL velocity (pixels per second). It does NOT represent real-world
km/h unless calibrated with homography matrices and camera intrinsics.
"""

from __future__ import annotations

import math
from typing import Literal

from app.config import get_settings
from app.tracking.tracker import TrackState

ActivityLabel = Literal["stationary", "walking", "running"]


class MovementAnalyzer:
    """Analyzes recent kinematic trajectory of tracked persons."""

    def __init__(
        self,
        stationary_speed_px: float | None = None,
        running_speed_px: float | None = None,
        normalize_by_height: bool | None = None,
        window_seconds: float = 1.0,
    ) -> None:
        settings = get_settings()
        self.stationary_thresh = stationary_speed_px or settings.stationary_speed_px
        self.running_thresh = running_speed_px or settings.running_speed_px
        self.normalize_by_height = (
            normalize_by_height if normalize_by_height is not None else settings.speed_normalize_by_height
        )
        self.window_seconds = window_seconds

    def update_track(self, track: TrackState) -> ActivityLabel:
        """Calculate velocity, durations, and update activity_state on the TrackState.

        Returns:
            Activity classification: "stationary" | "walking" | "running"
        """
        history = track.history
        if len(history) < 2:
            track.activity_state = "stationary"
            track.pixel_velocity = 0.0
            return "stationary"

        # Find points within the last window_seconds
        latest = history[-1]
        t_now = latest.timestamp

        # Scan backwards to find the point approximately `window_seconds` ago
        past_point = history[0]
        for pt in reversed(history):
            if (t_now - pt.timestamp) >= self.window_seconds:
                past_point = pt
                break

        dt = t_now - past_point.timestamp
        if dt <= 0.001:
            return track.activity_state  # type: ignore[return-value]

        dx = latest.center[0] - past_point.center[0]
        dy = latest.center[1] - past_point.center[1]
        dist_px = math.hypot(dx, dy)
        velocity_px_s = dist_px / dt

        # Optional height-based scale normalization (persons further away occupy fewer pixels)
        # Using a reference height of 200px
        effective_speed = velocity_px_s
        h = max(20.0, track.bbox[3] - track.bbox[1])
        if self.normalize_by_height and h > 0:
            scale_factor = 200.0 / h
            effective_speed = velocity_px_s * scale_factor

        track.pixel_velocity = round(velocity_px_s, 1)

        # Classify activity
        if effective_speed < self.stationary_thresh:
            activity: ActivityLabel = "stationary"
            track.stationary_duration += dt
            track.movement_duration = 0.0
        elif effective_speed >= self.running_thresh:
            activity = "running"
            track.movement_duration += dt
            track.stationary_duration = 0.0
        else:
            activity = "walking"
            track.movement_duration += dt
            track.stationary_duration = 0.0

        track.activity_state = activity
        return activity
