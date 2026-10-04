"""Structured logging for the backend (same schema as the AI engine).

Every log record can carry the Safe City context fields required by the spec:
``timestamp, service, camera_id, track_id, event, severity``.

Usage::

    from app.core.logger import get_logger, setup_logging

    setup_logging()                      # once, at process start
    log = get_logger(__name__)
    log.info("Restricted zone entry detected",
             extra={"camera_id": "CAM-001", "track_id": 23,
                    "event": "restricted_zone_entry", "severity": "HIGH"})

    # or bind context once for a camera worker:
    cam_log = get_logger(__name__, camera_id="CAM-001")
    cam_log.warning("Camera stream lost")

Privacy: never log frames, image bytes, credentials or RTSP passwords.
Use ``redact_url()`` before logging any source URL.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime
from typing import Any

CONTEXT_FIELDS: tuple[str, ...] = ("camera_id", "track_id", "event", "severity")

_SERVICE_NAME = "backend"
_CONFIGURED = False
_HANDLER: logging.Handler | None = None
_URL_CREDENTIALS = re.compile(r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*://)(?P<creds>[^/@\s]+)@")


def redact_url(url: str) -> str:
    """Hide credentials in URLs, e.g. ``rtsp://user:pass@host`` -> ``rtsp://***@host``."""
    return _URL_CREDENTIALS.sub(r"\g<scheme>***@", url)


class JsonFormatter(logging.Formatter):
    """One JSON object per line â€” ready for Loki/ELK/CloudWatch ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": _SERVICE_NAME,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in CONTEXT_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Readable single-line format for local development."""

    _COLORS = {
        "DEBUG": "\033[36m", "INFO": "\033[32m", "WARNING": "\033[33m",
        "ERROR": "\033[31m", "CRITICAL": "\033[41m",
    }
    _RESET = "\033[0m"

    def __init__(self, use_color: bool = True) -> None:
        super().__init__()
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        level = f"{record.levelname:<8}"
        if self.use_color:
            level = f"{self._COLORS.get(record.levelname, '')}{level}{self._RESET}"
        ctx = " ".join(
            f"{field}={getattr(record, field)}"
            for field in CONTEXT_FIELDS
            if getattr(record, field, None) is not None
        )
        line = f"{ts} {level} [{_SERVICE_NAME}] {record.name}: {record.getMessage()}"
        if ctx:
            line += f"  | {ctx}"
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that merges bound context (e.g. camera_id) into every record."""

    def process(self, msg: Any, kwargs: MutableMapping[str, Any]) -> tuple[Any, MutableMapping[str, Any]]:
        extra = dict(self.extra or {})
        extra.update(kwargs.get("extra") or {})
        kwargs["extra"] = extra
        return msg, kwargs

    def bind(self, **context: Any) -> ContextLogger:
        """Return a child logger with additional bound context."""
        merged: dict[str, Any] = dict(self.extra or {})
        merged.update(context)
        return ContextLogger(self.logger, merged)


def setup_logging(
    level: str | None = None,
    fmt: str | None = None,
    service_name: str | None = None,
) -> None:
    """Configure root logging once. Safe to call multiple times."""
    global _CONFIGURED, _SERVICE_NAME, _HANDLER

    if level is None or fmt is None or service_name is None:
        from app.config import get_settings  # local import avoids a circular import

        settings = get_settings()
        level = level or settings.log_level
        fmt = fmt or settings.log_format
        service_name = service_name or settings.service_name

    _SERVICE_NAME = service_name
    handler = logging.StreamHandler(sys.stdout)
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(ConsoleFormatter(use_color=sys.stdout.isatty()))

    root = logging.getLogger()
    if _HANDLER is not None:  # replace only our own handler; keep others (pytest, uvicorn)
        root.removeHandler(_HANDLER)
    root.addHandler(handler)
    _HANDLER = handler
    root.setLevel(level.upper())

    # Quieten chatty third-party libraries.
    for noisy in ("sqlalchemy.engine", "urllib3", "httpx", "httpcore", "asyncio", "aiosqlite"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str, **context: Any) -> ContextLogger:
    """Return a context-aware logger. Bound ``context`` keys should be from CONTEXT_FIELDS."""
    if not _CONFIGURED:
        setup_logging()
    return ContextLogger(logging.getLogger(name), dict(context))


def context_from(mapping: Mapping[str, Any]) -> dict[str, Any]:
    """Pick only the allowed context fields from an arbitrary mapping (e.g. an event dict)."""
    return {k: mapping[k] for k in CONTEXT_FIELDS if k in mapping and mapping[k] is not None}
