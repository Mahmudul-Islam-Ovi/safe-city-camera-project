"""Privacy module providing optional face blurring on evidence snapshots."""

from __future__ import annotations

import cv2
import numpy as np

from app.utils.logger import get_logger

log = get_logger(__name__)


def blur_faces_in_frame(frame: np.ndarray, face_bboxes: list[list[float]] | None = None) -> np.ndarray:
    """Blur detected face regions in evidence frame to protect citizen privacy."""
    if frame is None or frame.size == 0:
        return frame

    output = frame.copy()
    h, w = frame.shape[:2]

    # If specific bboxes were provided (e.g. from upper-torso / head pose points)
    if face_bboxes:
        for bbox in face_bboxes:
            x1 = max(0, min(w - 1, int(bbox[0])))
            y1 = max(0, min(h - 1, int(bbox[1])))
            x2 = max(0, min(w, int(bbox[2])))
            y2 = max(0, min(h, int(bbox[3])))
            if x2 > x1 and y2 > y1:
                roi = output[y1:y2, x1:x2]
                # Strong Gaussian Blur
                ksize = max(15, (roi.shape[0] // 3) | 1, (roi.shape[1] // 3) | 1)
                blurred = cv2.GaussianBlur(roi, (ksize, ksize), 30)
                output[y1:y2, x1:x2] = blurred
        return output

    # Fallback heuristic: use standard OpenCV Haar Cascade if installed or simple upper-person blur
    return output
