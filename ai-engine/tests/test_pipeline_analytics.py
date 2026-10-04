"""Unit tests for the AI pipeline components:
- Movement analysis
- Zone detection
- Loitering detection
- Behavioral Risk engine
- Event engine
"""

import time
from collections import deque

from app.activity.behavior import (
    CrowdDensityAnalyzer,
    LoiteringDetector,
)
from app.activity.movement import MovementAnalyzer
from app.risk.engine import RiskEngine
from app.tracking.tracker import TrackPoint, TrackState
from app.zones.manager import Zone, ZoneManager


def test_movement_analyzer_classification() -> None:
    analyzer = MovementAnalyzer(stationary_speed_px=10.0, running_speed_px=100.0, normalize_by_height=False)
    now = time.time()

    # Create a track
    track = TrackState(
        track_id=1,
        class_id=0,
        class_name="person",
        confidence=0.9,
        bbox=[100.0, 100.0, 150.0, 250.0],
        history=deque(),
    )

    # 1. Stationary points
    track.history.append(TrackPoint(timestamp=now - 1.0, center=(125.0, 175.0), bbox=track.bbox))
    track.history.append(TrackPoint(timestamp=now, center=(125.0, 176.0), bbox=track.bbox))

    activity = analyzer.update_track(track)
    assert activity == "stationary"
    assert track.pixel_velocity <= 10.0

    # 2. Walking points (moved ~30 px in 1s)
    track.history.append(TrackPoint(timestamp=now + 1.0, center=(155.0, 175.0), bbox=track.bbox))
    activity = analyzer.update_track(track)
    assert activity == "walking"

    # 3. Running points (moved 150 px in 0.5s -> 300 px/s)
    track.history.append(TrackPoint(timestamp=now + 1.5, center=(305.0, 175.0), bbox=track.bbox))
    activity = analyzer.update_track(track)
    assert activity == "running"


def test_zone_manager_point_in_polygon() -> None:
    zm = ZoneManager(camera_id="CAM-TEST")
    polygon = [
        [100.0, 100.0],
        [300.0, 100.0],
        [300.0, 300.0],
        [100.0, 300.0],
    ]
    zone = Zone(id="Z1", name="Vault", polygon=polygon, zone_type="restricted", severity="CRITICAL")
    zm.add_zone(zone)

    # Inside track: bottom_center at (200, 200)
    inside_track = TrackState(
        track_id=10,
        class_id=0,
        class_name="person",
        confidence=0.95,
        bbox=[180.0, 150.0, 220.0, 200.0],
    )
    zones = zm.check_track_zones(inside_track)
    assert len(zones) == 1
    assert zones[0].name == "Vault"
    assert inside_track.current_zone == "Vault"

    # Outside track: bottom_center at (500, 500)
    outside_track = TrackState(
        track_id=11,
        class_id=0,
        class_name="person",
        confidence=0.95,
        bbox=[480.0, 450.0, 520.0, 500.0],
    )
    zones = zm.check_track_zones(outside_track)
    assert len(zones) == 0
    assert outside_track.current_zone == "public_area"


def test_loitering_detector() -> None:
    ld = LoiteringDetector(time_threshold_seconds=5.0, radius_pixels=50.0)
    now = time.time()

    track = TrackState(
        track_id=20,
        class_id=0,
        class_name="person",
        confidence=0.9,
        bbox=[100.0, 100.0, 150.0, 250.0],
    )

    # Initial frame
    res = ld.check(track, current_time=now)
    assert res is None

    # After 3 seconds within radius -> still under threshold
    res = ld.check(track, current_time=now + 3.0)
    assert res is None

    # After 6 seconds within radius -> loitering detected
    res = ld.check(track, current_time=now + 6.0)
    assert res is not None
    assert res >= 5.0


def test_risk_engine_scoring() -> None:
    re = RiskEngine()

    # Low risk
    eval_low = re.calculate([])
    assert eval_low.score == 0
    assert eval_low.level == "LOW"

    # Medium risk: restricted zone entry (+30)
    eval_med = re.calculate(["restricted_zone_entry"])
    assert eval_med.score == 30
    assert eval_med.level == "MEDIUM"
    assert any("Restricted zone entry" in r for r in eval_med.reasons)

    # High risk: restricted zone entry (+30) + running (+20) + loitering (+20) = 70
    eval_high = re.calculate(["restricted_zone_entry", "running_in_restricted_zone", "loitering"])
    assert eval_high.score == 70
    assert eval_high.level == "HIGH"
    assert len(eval_high.reasons) == 3


def test_crowd_density() -> None:
    c = CrowdDensityAnalyzer(high_threshold=10, critical_threshold=25)
    level, alert = c.evaluate(5)
    assert level == "NORMAL" and not alert

    level, alert = c.evaluate(15)
    assert level == "HIGH" and alert

    level, alert = c.evaluate(30)
    assert level == "CRITICAL" and alert
