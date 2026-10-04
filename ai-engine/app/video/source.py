"""Video source abstractions for Safe City AI.

Provides a unified interface (VideoSource) supporting:
- WebcamSource: laptop built-in webcam or USB camera (OpenCV DirectShow / V4L2)
- FileSource: MP4 / AVI surveillance video files (with optional looping)
- RTSPSource: CCTV / IP camera streams (with auto-reconnect logic)
"""

from __future__ import annotations

import platform
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.utils.logger import get_logger, redact_url

log = get_logger(__name__)


@dataclass
class VideoMetadata:
    """Metadata describing a video source."""
    source_type: str
    width: int
    height: int
    fps: float
    total_frames: int = 0
    uri: str = ""


class VideoSource(ABC):
    """Abstract base class for all video sources."""

    def __init__(self, camera_id: str = "CAM-001") -> None:
        self.camera_id = camera_id
        self._is_opened: bool = False
        self._metadata: VideoMetadata | None = None
        self._frame_count: int = 0

    @property
    def is_opened(self) -> bool:
        return self._is_opened

    @property
    def metadata(self) -> VideoMetadata:
        if self._metadata is None:
            raise RuntimeError("VideoSource is not opened yet")
        return self._metadata

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @abstractmethod
    def open(self) -> bool:
        """Open the video stream. Returns True if successfully opened."""
        pass

    @abstractmethod
    def read(self) -> tuple[bool, np.ndarray | None]:
        """Read the next video frame.

        Returns:
            (success, frame_bgr)
        """
        pass

    @abstractmethod
    def release(self) -> None:
        """Release underlying hardware or file resources."""
        pass

    def __enter__(self) -> VideoSource:
        if not self.open():
            raise RuntimeError(f"Failed to open video source for {self.camera_id}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()


class WebcamSource(VideoSource):
    """Captures video from a local laptop or USB webcam."""

    def __init__(
        self,
        camera_index: int = 0,
        camera_id: str = "CAM-001",
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        super().__init__(camera_id=camera_id)
        self.camera_index = camera_index
        self.desired_width = width
        self.desired_height = height
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> bool:
        backend = cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_ANY
        log.info("Opening webcam", extra={"camera_id": self.camera_id, "event": f"webcam_index_{self.camera_index}"})
        self._cap = cv2.VideoCapture(self.camera_index, backend)
        if not self._cap.isOpened():
            log.error("Failed to open webcam", extra={"camera_id": self.camera_id, "severity": "HIGH"})
            self._is_opened = False
            return False

        if self.desired_width and self.desired_height:
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.desired_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.desired_height)

        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0

        self._metadata = VideoMetadata(
            source_type="webcam",
            width=actual_w,
            height=actual_h,
            fps=fps,
            uri=f"webcam://{self.camera_index}",
        )
        self._is_opened = True
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._is_opened or self._cap is None:
            return False, None
        success, frame = self._cap.read()
        if success and frame is not None:
            self._frame_count += 1
            return True, frame
        return False, None

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_opened = False
        log.info("Webcam released", extra={"camera_id": self.camera_id})


class FileSource(VideoSource):
    """Reads video from an MP4, AVI, or MKV file with optional looping."""

    def __init__(
        self,
        file_path: str | Path,
        camera_id: str = "CAM-001",
        loop: bool = True,
    ) -> None:
        super().__init__(camera_id=camera_id)
        self.file_path = Path(file_path).resolve()
        self.loop = loop
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> bool:
        if not self.file_path.exists():
            log.error("Video file does not exist: %s", self.file_path, extra={"camera_id": self.camera_id})
            return False

        log.info("Opening video file: %s", self.file_path.name, extra={"camera_id": self.camera_id})
        self._cap = cv2.VideoCapture(str(self.file_path))
        if not self._cap.isOpened():
            log.error("Failed to open video file %s", self.file_path, extra={"camera_id": self.camera_id})
            self._is_opened = False
            return False

        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 25.0
        total = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self._metadata = VideoMetadata(
            source_type="file",
            width=w,
            height=h,
            fps=fps,
            total_frames=total,
            uri=str(self.file_path),
        )
        self._is_opened = True
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._is_opened or self._cap is None:
            return False, None
        success, frame = self._cap.read()
        if not success or frame is None:
            if self.loop:
                # Loop back to beginning
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = self._cap.read()
                if success and frame is not None:
                    self._frame_count += 1
                    return True, frame
            return False, None
        self._frame_count += 1
        return True, frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_opened = False
        log.info("Video file released", extra={"camera_id": self.camera_id})


class RTSPSource(VideoSource):
    """Connects to a CCTV/IP camera over RTSP with automatic reconnect."""

    def __init__(
        self,
        rtsp_url: str,
        camera_id: str = "CAM-001",
        reconnect_delay_seconds: float = 3.0,
        max_reconnect_attempts: int = 5,
    ) -> None:
        super().__init__(camera_id=camera_id)
        self.rtsp_url = rtsp_url
        self.reconnect_delay = reconnect_delay_seconds
        self.max_attempts = max_reconnect_attempts
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> bool:
        redacted = redact_url(self.rtsp_url)
        log.info("Connecting to RTSP stream: %s", redacted, extra={"camera_id": self.camera_id})
        self._cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not self._cap.isOpened():
            log.warning("Failed to connect to RTSP stream %s", redacted, extra={"camera_id": self.camera_id})
            self._is_opened = False
            return False

        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 25.0

        self._metadata = VideoMetadata(
            source_type="rtsp",
            width=w,
            height=h,
            fps=fps,
            uri=redacted,
        )
        self._is_opened = True
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self._is_opened or self._cap is None:
            return False, None
        success, frame = self._cap.read()
        if not success or frame is None:
            log.warning("RTSP stream interrupted, attempting reconnect...", extra={"camera_id": self.camera_id})
            self.release()
            for attempt in range(1, self.max_attempts + 1):
                time.sleep(self.reconnect_delay)
                if self.open():
                    log.info("RTSP reconnected on attempt %d", attempt, extra={"camera_id": self.camera_id})
                    return self.read()
            return False, None
        self._frame_count += 1
        return True, frame

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._is_opened = False
