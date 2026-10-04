"""Polygon-based zone management and point-in-polygon containment analysis.

Allows operators to define named polygon zones with severity and type:
- restricted: triggers restricted_zone_entry event immediately
- warning: caution area
- perimeter: boundary monitoring
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from app.tracking.tracker import TrackState
from app.utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class Zone:
    """Represents a virtual geometric zone in camera view coordinates."""
    id: str
    name: str
    polygon: list[list[float]]  # [[x1, y1], [x2, y2], ...]
    zone_type: str = "restricted"  # restricted | warning | public | perimeter
    severity: str = "HIGH"         # LOW | MEDIUM | HIGH | CRITICAL
    enabled: bool = True
    camera_id: str = "CAM-001"

    def __post_init__(self) -> None:
        self._pts_np = np.array(self.polygon, dtype=np.int32).reshape((-1, 1, 2))

    def contains_point(self, pt: tuple[float, float]) -> bool:
        """Check if 2D coordinate is inside polygon (cv2.pointPolygonTest)."""
        if not self.enabled or len(self.polygon) < 3:
            return False
        # >= 0 means inside or on edge
        res = cv2.pointPolygonTest(self._pts_np, (float(pt[0]), float(pt[1])), measureDist=False)
        return res >= 0

    def contains_track(self, track: TrackState) -> bool:
        """Evaluate if a person is inside the zone using their bottom-center ground contact."""
        return self.contains_point(track.bottom_center)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "polygon": self.polygon,
            "zone_type": self.zone_type,
            "severity": self.severity,
            "enabled": self.enabled,
            "camera_id": self.camera_id,
        }


class ZoneManager:
    """Manages virtual zones for a camera feed."""

    def __init__(self, camera_id: str = "CAM-001") -> None:
        self.camera_id = camera_id
        self.zones: dict[str, Zone] = {}

    def add_zone(self, zone: Zone) -> None:
        self.zones[zone.id] = zone
        log.info("Zone registered: %s (%s, severity=%s)", zone.name, zone.zone_type, zone.severity)

    def remove_zone(self, zone_id: str) -> None:
        if zone_id in self.zones:
            del self.zones[zone_id]

    def check_track_zones(self, track: TrackState) -> list[Zone]:
        """Return list of active zones that currently contain this track."""
        active_zones: list[Zone] = []
        for zone in self.zones.values():
            if zone.enabled and zone.contains_track(track):
                active_zones.append(zone)

        # Update track's current zone description
        if active_zones:
            track.current_zone = active_zones[0].name
        else:
            track.current_zone = "public_area"

        return active_zones
