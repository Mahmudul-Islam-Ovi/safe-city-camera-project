"""Complete AI Processing Pipeline for Safe City AI.

Executes the full pipeline per frame:
Frame Extraction -> YOLO Detection -> Tracking -> Movement Analysis ->
Zone Analysis -> Behavioral Analytics (Loitering, Crowd, Abandoned, Aggression) ->
Risk Scoring -> Event Generation -> Visual Annotation
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import cv2
import numpy as np

from app.activity.behavior import (
    AbandonedObjectDetector,
    AggressiveActivityDetector,
    CrowdDensityAnalyzer,
    LoiteringDetector,
)
from app.activity.movement import MovementAnalyzer
from app.config import get_settings
from app.detection.detector import Detection, Detector
from app.events.engine import Event, EventEngine
from app.pipeline.annotator import Annotator
from app.pose.fall import FallDetector, PoseEstimator
from app.risk.engine import RiskEngine
from app.tracking.tracker import Tracker, TrackState
from app.utils.logger import get_logger
from app.zones.manager import Zone, ZoneManager

log = get_logger(__name__)


@dataclass
class PipelineOutput:
    annotated_frame: np.ndarray
    detections: list[Detection]
    tracks: list[TrackState]
    people_count: int
    events: list[Event]
    fps: float


class AIPipeline:
    """Orchestrates all computer vision and risk detection modules for one video stream."""

    def __init__(self, camera_id: str = "CAM-001", enable_pose: bool = True) -> None:
        self.camera_id = camera_id
        self.settings = get_settings()

        # Core modules
        self.detector = Detector()
        self.tracker = Tracker()
        self.movement = MovementAnalyzer()
        self.zone_manager = ZoneManager(camera_id=camera_id)
        self.loitering = LoiteringDetector()
        self.crowd = CrowdDensityAnalyzer()
        self.abandoned = AbandonedObjectDetector()
        self.aggression = AggressiveActivityDetector()
        self.risk_engine = RiskEngine()
        self.event_engine = EventEngine()
        self.annotator = Annotator()

        self.enable_pose = enable_pose and self.settings.pose_enabled
        self.pose_estimator = PoseEstimator() if self.enable_pose else None
        self.fall_detector = FallDetector() if self.enable_pose else None

        self._frame_count = 0
        self._last_time = time.time()
        self._fps = 0.0

    def add_demo_restricted_zone(self, frame_width: int, frame_height: int) -> None:
        """Add a default restricted zone for demonstration purposes if none exist."""
        if not self.zone_manager.zones:
            # Polygon in top-right / middle region
            w, h = frame_width, frame_height
            polygon = [
                [int(w * 0.45), int(h * 0.20)],
                [int(w * 0.95), int(h * 0.20)],
                [int(w * 0.95), int(h * 0.85)],
                [int(w * 0.45), int(h * 0.85)],
            ]
            self.zone_manager.add_zone(
                Zone(
                    id="ZONE-DEMO-01",
                    name="Restricted Zone Alpha",
                    polygon=polygon,
                    zone_type="restricted",
                    severity="HIGH",
                    camera_id=self.camera_id,
                )
            )

    def process_frame(self, frame: np.ndarray, timestamp: float | None = None) -> PipelineOutput:
        """Process a single video frame end-to-end."""
        now = timestamp or time.time()
        self._frame_count += 1

        # Calculate FPS
        dt = now - self._last_time
        if dt >= 1.0:
            self._fps = self._frame_count / dt
            self._frame_count = 0
            self._last_time = now

        # Resize if PROCESS_WIDTH is set
        pw = self.settings.process_width
        if pw > 0 and frame.shape[1] > pw:
            scale = pw / frame.shape[1]
            frame = cv2.resize(frame, (pw, int(frame.shape[0] * scale)))

        h, w = frame.shape[:2]

        # 1. Object Detection
        detections = self.detector.detect(frame)

        # 2. Tracking
        tracks = self.tracker.track(frame, timestamp=now)
        person_tracks = [t for t in tracks if t.class_name == "person"]
        people_count = len(person_tracks)

        # 3. Movement analysis
        for t in person_tracks:
            self.movement.update_track(t)

        # 4. Pose and Fall Detection (optional)
        if self.enable_pose and self.pose_estimator and self.fall_detector:
            poses = self.pose_estimator.estimate(frame)
            if poses and person_tracks:
                # Match nearest pose to track
                for p, t in zip(poses, person_tracks, strict=False):
                    is_fall = self.fall_detector.check_fall(t, p.posture, timestamp=now)
                    if is_fall:
                        t.activity_state = "falling"

        # 5. Zone Analysis & Events
        new_events: list[Event] = []

        for t in person_tracks:
            active_zones = self.zone_manager.check_track_zones(t)
            for z in active_zones:
                if z.zone_type == "restricted":
                    observed = ["restricted_zone_entry"]
                    if t.activity_state == "running":
                        observed.append("running_in_restricted_zone")

                    risk = self.risk_engine.calculate(observed)
                    ev = self.event_engine.create_event(
                        camera_id=self.camera_id,
                        event_type="restricted_zone_entry",
                        confidence=t.confidence,
                        risk=risk,
                        track_id=t.track_id,
                        frame=frame,
                        metadata={"zone_name": z.name, "activity": t.activity_state},
                    )
                    if ev:
                        new_events.append(ev)

        # 6. Loitering Detection
        for t in person_tracks:
            loitering_duration = self.loitering.check(t, current_time=now)
            if loitering_duration is not None:
                risk = self.risk_engine.calculate(["loitering"])
                ev = self.event_engine.create_event(
                    camera_id=self.camera_id,
                    event_type="loitering",
                    confidence=0.88,
                    risk=risk,
                    track_id=t.track_id,
                    frame=frame,
                    metadata={"duration_seconds": loitering_duration},
                )
                if ev:
                    new_events.append(ev)

        # 7. Fall Events
        for t in person_tracks:
            if t.activity_state == "falling":
                risk = self.risk_engine.calculate(["fall_detected"])
                ev = self.event_engine.create_event(
                    camera_id=self.camera_id,
                    event_type="fall_detected",
                    confidence=0.82,
                    risk=risk,
                    track_id=t.track_id,
                    frame=frame,
                )
                if ev:
                    new_events.append(ev)

        # 8. Crowd Density Analysis
        crowd_level, crowd_alert = self.crowd.evaluate(people_count)
        if crowd_alert:
            ev_type = "critical_crowd_density" if crowd_level == "CRITICAL" else "high_crowd_density"
            risk = self.risk_engine.calculate([ev_type])
            ev = self.event_engine.create_event(
                camera_id=self.camera_id,
                event_type=ev_type,
                confidence=0.95,
                risk=risk,
                frame=frame,
                metadata={"people_count": people_count},
            )
            if ev:
                new_events.append(ev)

        # 9. Abandoned Objects
        abandoned_items = self.abandoned.update(detections, person_tracks, timestamp=now)
        for item in abandoned_items:
            risk = self.risk_engine.calculate(["possible_abandoned_object"])
            ev = self.event_engine.create_event(
                camera_id=self.camera_id,
                event_type="possible_abandoned_object",
                confidence=item["confidence"],
                risk=risk,
                frame=frame,
                metadata=item,
            )
            if ev:
                new_events.append(ev)

        # 10. Aggressive Activity
        aggression_events = self.aggression.check(person_tracks)
        for agg in aggression_events:
            risk = self.risk_engine.calculate(["possible_aggressive_activity"])
            ev = self.event_engine.create_event(
                camera_id=self.camera_id,
                event_type="possible_aggressive_activity",
                confidence=agg["confidence"],
                risk=risk,
                frame=frame,
                metadata=agg,
            )
            if ev:
                new_events.append(ev)

        # 11. Visual Annotation
        annotated = frame.copy()
        annotated = self.annotator.draw_zones(annotated, list(self.zone_manager.zones.values()))
        annotated = self.annotator.draw_tracks(annotated, tracks)
        annotated = self.annotator.draw_banner(annotated, self.camera_id, people_count, new_events)

        return PipelineOutput(
            annotated_frame=annotated,
            detections=detections,
            tracks=tracks,
            people_count=people_count,
            events=new_events,
            fps=self._fps,
        )
