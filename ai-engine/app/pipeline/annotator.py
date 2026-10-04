"""Visual annotator for drawing detections, track IDs, activity labels, zones, and risk overlays."""

from __future__ import annotations

import cv2
import numpy as np

from app.events.engine import Event
from app.tracking.tracker import TrackState
from app.zones.manager import Zone

# Colors in BGR
COLOR_GREEN = (46, 204, 113)
COLOR_YELLOW = (41, 128, 185)
COLOR_ORANGE = (39, 174, 96)
COLOR_RED = (41, 41, 231)
COLOR_CYAN = (241, 196, 15)
COLOR_WHITE = (255, 255, 255)
COLOR_DARK = (20, 20, 20)


class Annotator:
    """Renders real-time computer vision overlays onto frames."""

    @staticmethod
    def draw_zones(frame: np.ndarray, zones: list[Zone]) -> np.ndarray:
        for z in zones:
            if not z.enabled or len(z.polygon) < 3:
                continue
            pts = np.array(z.polygon, dtype=np.int32).reshape((-1, 1, 2))
            # Semi-transparent fill
            overlay = frame.copy()
            color = COLOR_RED if z.zone_type == "restricted" else COLOR_CYAN
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

            # Border
            cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2)

            # Zone label
            top_pt = pts[0][0]
            cv2.putText(
                frame,
                f"ZONE: {z.name} ({z.severity})",
                (int(top_pt[0]), max(20, int(top_pt[1]) - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )
        return frame

    @staticmethod
    def draw_tracks(frame: np.ndarray, tracks: list[TrackState]) -> np.ndarray:
        for t in tracks:
            x1, y1, x2, y2 = [int(v) for v in t.bbox]

            # Choose color based on activity
            if t.activity_state == "running":
                box_color = COLOR_ORANGE
            elif t.activity_state == "walking":
                box_color = COLOR_GREEN
            elif t.posture == "lying":
                box_color = COLOR_RED
            else:
                box_color = COLOR_CYAN

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

            # Label banner
            label = f"ID:{t.track_id} {t.class_name} | {t.activity_state.upper()}"
            if t.current_zone != "public_area":
                label += f" | {t.current_zone}"

            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, max(0, y1 - 22)), (x1 + lw + 8, y1), box_color, -1)
            cv2.putText(
                frame,
                label,
                (x1 + 4, max(14, y1 - 6)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                COLOR_DARK if box_color != COLOR_DARK else COLOR_WHITE,
                1,
                cv2.LINE_AA,
            )

            # Trajectory history tail
            if len(t.history) > 1:
                pts = [np.array([int(pt.center[0]), int(pt.center[1])]) for pt in t.history]
                for i in range(1, len(pts)):
                    cv2.line(frame, tuple(pts[i - 1]), tuple(pts[i]), box_color, 1, cv2.LINE_AA)

        return frame

    @staticmethod
    def draw_banner(
        frame: np.ndarray,
        camera_id: str,
        people_count: int,
        active_events: list[Event],
    ) -> np.ndarray:
        """Top HUD banner showing camera ID, crowd count, and latest event alert."""
        h, w = frame.shape[:2]
        # Dark top strip
        cv2.rectangle(frame, (0, 0), (w, 36), (15, 15, 15), -1)

        # Status text
        hud_text = f"CAM: {camera_id}  |  PEOPLE: {people_count}"
        cv2.putText(frame, hud_text, (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_WHITE, 2, cv2.LINE_AA)

        if active_events:
            latest = active_events[-1]
            alert_color = COLOR_RED if latest.risk_level in ("HIGH", "CRITICAL") else COLOR_ORANGE
            alert_text = f"ALERT: {latest.event_type.upper()} ({latest.risk_level} - {latest.risk_score})"
            cv2.putText(frame, alert_text, (w - 480, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, alert_color, 2, cv2.LINE_AA)

        return frame
