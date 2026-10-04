"""Pose estimation and Fall Detection using YOLO Pose.

Observes temporal transition:
standing / sitting -> rapid posture change -> horizontal body orientation -> possible fall.

IMPORTANT:
This is an automated computer vision observation for operator awareness,
NOT a medical diagnostic tool.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO

from app.config import get_settings
from app.tracking.tracker import TrackState
from app.utils.device import resolve_device
from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class PoseData:
    keypoints: np.ndarray  # [17, 3] (x, y, conf)
    posture: str          # standing | sitting | lying


class PoseEstimator:
    """Ultralytics YOLO Pose wrapper."""

    def __init__(self, model_name: str | None = None, device: str | None = None) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.yolo_pose_model
        self.device = resolve_device(device or settings.device)
        self.imgsz = settings.inference_image_size
        weights_path = settings.model_file(self.model_name)
        log.info("Loading YOLO Pose model: %s on %s", weights_path.name, self.device)
        self.model = YOLO(str(weights_path))

    def estimate(self, frame: np.ndarray) -> list[PoseData]:
        if frame is None or frame.size == 0:
            return []

        results = self.model.predict(
            source=frame,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False,
            conf=0.35,
        )
        if not results:
            return []

        r = results[0]
        if r.keypoints is None or len(r.keypoints) == 0:
            return []

        poses: list[PoseData] = []
        kpts_data = r.keypoints.data.cpu().numpy()  # [N, 17, 3]

        for kpts in kpts_data:
            posture = self._classify_posture(kpts)
            poses.append(PoseData(keypoints=kpts, posture=posture))

        return poses

    def _classify_posture(self, kpts: np.ndarray) -> str:
        """Heuristic posture classification using keypoint orientations."""
        # Keypoints: 0:nose, 5:l_shoulder, 6:r_shoulder, 11:l_hip, 12:r_hip, 15:l_ankle, 16:r_ankle
        try:
            head_y = kpts[0, 1] if kpts[0, 2] > 0.25 else min(kpts[5, 1], kpts[6, 1])
            hip_y = (kpts[11, 1] + kpts[12, 1]) / 2.0
            ankle_y = (kpts[15, 1] + kpts[16, 1]) / 2.0

            # Compute aspect ratio of torso/legs
            torso_height = abs(hip_y - head_y)
            leg_height = abs(ankle_y - hip_y)
            total_vertical = torso_height + leg_height

            shoulder_w = abs(kpts[5, 0] - kpts[6, 0])
            hip_w = abs(kpts[11, 0] - kpts[12, 0])
            horizontal_span = max(shoulder_w, hip_w, 20.0)

            # If body is oriented horizontally (lying down)
            if total_vertical < horizontal_span * 0.8:
                return "lying"

            # If legs are compressed relative to torso
            if leg_height < torso_height * 0.7:
                return "sitting"

            return "standing"
        except Exception:
            return "standing"


class FallDetector:
    """Monitors posture transitions over time to flag possible falls."""

    def __init__(self, rapid_fall_seconds: float = 1.2) -> None:
        self.rapid_fall_seconds = rapid_fall_seconds
        # track_id -> (last_posture, timestamp_of_change)
        self._history: dict[int, tuple[str, float]] = {}

    def check_fall(self, track: TrackState, current_posture: str, timestamp: float | None = None) -> bool:
        now = timestamp or time.time()
        tid = track.track_id

        if tid not in self._history:
            self._history[tid] = (current_posture, now)
            track.posture = current_posture
            return False

        last_posture, change_time = self._history[tid]

        # Transition: was standing/sitting, now suddenly lying
        if last_posture in ("standing", "sitting") and current_posture == "lying":
            elapsed = now - change_time
            if elapsed <= self.rapid_fall_seconds:
                log.info("Possible fall detected for track %d (transitioned in %.2fs)", tid, elapsed)
                self._history[tid] = (current_posture, now)
                track.posture = current_posture
                return True

        if last_posture != current_posture:
            self._history[tid] = (current_posture, now)

        track.posture = current_posture
        return False
