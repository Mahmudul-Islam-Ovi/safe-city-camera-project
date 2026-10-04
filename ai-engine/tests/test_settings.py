"""Phase 1 tests: configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config.settings import PROJECT_ROOT, Settings, get_settings


def make(**overrides: object) -> Settings:
    """Build settings without reading .env files, so tests are deterministic."""
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_defaults_are_sane() -> None:
    s = make()
    assert s.service_name == "ai-engine"
    assert 0 < s.confidence_threshold <= 1
    assert "person" in s.detection_classes
    assert s.tracker_type == "bytetrack"
    assert s.store_raw_video is False, "privacy: raw video must not be stored by default"
    assert s.face_blur_enabled is True


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOITERING_TIME_SECONDS", "45")
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.65")
    monkeypatch.setenv("TRACKER_TYPE", "botsort")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.loitering_time_seconds == 45
    assert s.confidence_threshold == pytest.approx(0.65)
    assert s.tracker_type == "botsort"


def test_detection_classes_comma_separated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DETECTION_CLASSES", " Person, car ,person,backpack ")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.detection_classes == ["person", "car", "backpack"]  # lower-cased, de-duplicated, ordered


def test_unknown_detection_class_rejected() -> None:
    with pytest.raises(ValidationError, match="Unsupported detection classes"):
        make(detection_classes="person,unicorn")


@pytest.mark.parametrize("value", [0.0, 1.5, -0.2])
def test_confidence_out_of_range_rejected(value: float) -> None:
    with pytest.raises(ValidationError):
        make(confidence_threshold=value)


def test_running_must_exceed_stationary() -> None:
    with pytest.raises(ValidationError, match="RUNNING_SPEED_PX"):
        make(stationary_speed_px=200, running_speed_px=100)


def test_crowd_critical_must_exceed_high() -> None:
    with pytest.raises(ValidationError, match="CROWD_CRITICAL_THRESHOLD"):
        make(crowd_threshold=40, crowd_critical_threshold=30)


@pytest.mark.parametrize("device", ["auto", "cpu", "cuda", "cuda:1", "0", "mps", "CPU"])
def test_valid_devices(device: str) -> None:
    assert make(device=device).device == device.lower()


def test_invalid_device_rejected() -> None:
    with pytest.raises(ValidationError):
        make(device="tpu")


def test_relative_paths_resolve_against_project_root() -> None:
    s = make(evidence_dir="evidence", risk_rules_file="configs/risk_rules.yaml")
    assert s.evidence_path == (PROJECT_ROOT / "evidence").resolve()
    assert s.risk_rules_path == (PROJECT_ROOT / "configs" / "risk_rules.yaml").resolve()


def test_absolute_paths_kept(tmp_path: Path) -> None:
    s = make(evidence_dir=tmp_path)
    assert s.evidence_path == tmp_path


def test_model_file_inside_models_dir() -> None:
    s = make()
    assert s.model_file("yolo11n.pt") == s.models_path / "yolo11n.pt"


def test_min_frame_interval() -> None:
    assert make(inference_fps=10).min_frame_interval == pytest.approx(0.1)


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


def test_env_example_has_no_unknown_keys() -> None:
    """Every AI-related key in .env.example must be a real setting (catches typos)."""
    example = PROJECT_ROOT / ".env.example"
    assert example.exists(), ".env.example missing at project root"
    fields = set(Settings.model_fields)
    ai_keys = {
        "YOLO_MODEL", "CONFIDENCE_THRESHOLD", "LOITERING_TIME_SECONDS", "LOITERING_RADIUS_PIXELS",
        "CROWD_THRESHOLD", "TRACKER_TYPE", "INFERENCE_FPS", "FRAME_SKIP", "DEVICE", "FACE_BLUR_ENABLED",
    }
    present = {
        line.split("=", 1)[0].strip()
        for line in example.read_text(encoding="utf-8").splitlines()
        if "=" in line and not line.lstrip().startswith("#")
    }
    missing_in_example = ai_keys - present
    assert not missing_in_example, f".env.example lacks required keys: {missing_in_example}"
    for key in ai_keys:
        assert key.lower() in fields, f"{key} is not a Settings field"


def test_env_example_parses_into_valid_settings() -> None:
    """The shipped .env.example (with inline comments) must load cleanly."""
    s = Settings(_env_file=PROJECT_ROOT / ".env.example")  # type: ignore[call-arg]
    assert s.tracker_type == "bytetrack"
    assert s.loitering_time_seconds == 120
    assert s.log_format == "console"
