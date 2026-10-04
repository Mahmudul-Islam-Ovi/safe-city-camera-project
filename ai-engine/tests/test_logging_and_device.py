"""Phase 1 tests: structured logging and device fallback."""

from __future__ import annotations

import json
import logging

import pytest

from app.utils.device import resolve_device
from app.utils.logger import JsonFormatter, context_from, get_logger, redact_url, setup_logging


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord("test", logging.WARNING, __file__, 1, "Restricted zone entry detected", None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_contains_required_fields() -> None:
    setup_logging(level="INFO", fmt="json", service_name="ai-engine")
    line = JsonFormatter().format(
        _record(camera_id="CAM-001", track_id=23, event="restricted_zone_entry", severity="HIGH")
    )
    payload = json.loads(line)
    for key in ("timestamp", "service", "camera_id", "track_id", "event", "severity", "message", "level"):
        assert key in payload, f"missing {key}"
    assert payload["service"] == "ai-engine"
    assert payload["track_id"] == 23


def test_json_formatter_omits_empty_context() -> None:
    payload = json.loads(JsonFormatter().format(_record()))
    assert "camera_id" not in payload and "track_id" not in payload


def test_bound_context_is_merged(caplog: pytest.LogCaptureFixture) -> None:
    setup_logging(level="DEBUG", fmt="console", service_name="ai-engine")
    log = get_logger("safe_city.test", camera_id="CAM-007")
    with caplog.at_level(logging.INFO):
        log.bind(track_id=5).info("track created", extra={"event": "track_created"})
    rec = caplog.records[-1]
    assert rec.camera_id == "CAM-007"
    assert rec.track_id == 5
    assert rec.event == "track_created"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("rtsp://admin:S3cret@192.168.1.10:554/stream1", "rtsp://***@192.168.1.10:554/stream1"),
        ("rtsp://192.168.1.10/stream", "rtsp://192.168.1.10/stream"),
        ("http://user@host/x", "http://***@host/x"),
    ],
)
def test_redact_url(raw: str, expected: str) -> None:
    assert redact_url(raw) == expected


def test_context_from_filters_keys() -> None:
    data = {"camera_id": "CAM-1", "track_id": None, "event": "loitering", "frame": b"\x00\x01"}
    assert context_from(data) == {"camera_id": "CAM-1", "event": "loitering"}


def test_resolve_device_cpu_always_works() -> None:
    assert resolve_device("cpu") == "cpu"


def test_resolve_device_auto_returns_valid_value() -> None:
    assert resolve_device("auto") in {"cpu", "mps"} or resolve_device("auto").startswith("cuda:")


def test_resolve_device_missing_gpu_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    import torch

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert resolve_device("cuda:3") == "cpu"
    assert resolve_device("cuda") == "cpu"
