"""Object detection schemas and Detector implementation using Ultralytics YOLO.

Adheres strictly to the Safe City AI requirements:
- Returns structured detection dictionaries/objects:
  {"class_id": 0, "class_name": "person", "confidence": 0.94, "bbox": [x1, y1, x2, y2]}
- Filter by configured classes (person priority, vehicle, animals, bags)
- Configurable confidence and IOU thresholds from Settings / env vars
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from ultralytics import YOLO

from app.config import get_settings
from app.utils.device import resolve_device
from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class Detection:
    """Structured representation of a single detected object in a frame."""
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]

    @property
    def x1(self) -> float:
        return self.bbox[0]

    @property
    def y1(self) -> float:
        return self.bbox[1]

    @property
    def x2(self) -> float:
        return self.bbox[2]

    @property
    def y2(self) -> float:
        return self.bbox[3]

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    @property
    def bottom_center(self) -> tuple[float, float]:
        """Useful for foot/ground position in perspective and zone analysis."""
        return ((self.x1 + self.x2) / 2.0, self.y2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "confidence": round(float(self.confidence), 3),
            "bbox": [round(float(c), 1) for c in self.bbox],
            "center": [round(c, 1) for c in self.center],
        }


class Detector:
    """Ultralytics YOLO wrapper tailored for Safe City video analytics."""

    def __init__(
        self,
        model_name: str | None = None,
        confidence_threshold: float | None = None,
        iou_threshold: float | None = None,
        classes: list[str] | None = None,
        device: str | None = None,
    ) -> None:
        settings = get_settings()
        self.model_name = model_name or settings.yolo_model
        self.conf_threshold = confidence_threshold or settings.confidence_threshold
        self.iou_threshold = iou_threshold or settings.iou_threshold
        self.target_classes = set(classes or settings.detection_classes)
        self.device = resolve_device(device or settings.device)
        self.imgsz = settings.inference_image_size

        weights_path = settings.model_file(self.model_name)
        weights_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Loading YOLO model: %s on %s", weights_path.name, self.device)
        self.model = YOLO(str(weights_path))

        # Model class lookup: id -> name
        raw_names = self.model.names
        self.class_names: dict[int, str] = raw_names if isinstance(raw_names, dict) else dict(enumerate(raw_names))
        # Inverse lookup: name -> id
        self.name_to_id: dict[str, int] = {v: k for k, v in self.class_names.items()}

        # Allowed class IDs for quick filtering in YOLO inference
        self.allowed_class_ids: list[int] = [
            cid for cid, cname in self.class_names.items() if cname in self.target_classes
        ]

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run object detection on a BGR video frame.

        Returns:
            List of structured Detection objects matching configured classes and threshold.
        """
        if frame is None or frame.size == 0:
            return []

        results = self.model.predict(
            source=frame,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            classes=self.allowed_class_ids,
            imgsz=self.imgsz,
            device=self.device,
            verbose=False,
        )

        detections: list[Detection] = []
        if not results:
            return detections

        r = results[0]
        boxes = r.boxes
        if boxes is None or len(boxes) == 0:
            return detections

        xyxy_arr = boxes.xyxy.cpu().numpy()
        conf_arr = boxes.conf.cpu().numpy()
        cls_arr = boxes.cls.cpu().numpy()

        for xyxy, conf, cid_raw in zip(xyxy_arr, conf_arr, cls_arr, strict=False):
            cid = int(cid_raw)
            cname = self.class_names.get(cid, "unknown")
            if cname not in self.target_classes:
                continue

            detections.append(
                Detection(
                    class_id=cid,
                    class_name=cname,
                    confidence=float(conf),
                    bbox=[float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])],
                )
            )

        return detections
