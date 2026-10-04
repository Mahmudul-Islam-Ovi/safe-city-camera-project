"""SQLAlchemy ORM models for Safe City AI.

Tables:
- cameras
- zones
- events
- alerts
- system_settings
- audit_logs

Indexed heavily on camera_id, timestamp, event_type, and risk_level.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy import Boolean, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database.session import Base

# Compatible JSON column for SQLite and Postgres
JSONType = JSON().with_variant(JSONB, "postgresql")


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(256), default="Main Entrance")
    source_type: Mapped[str] = mapped_column(String(32), default="WEBCAM")  # WEBCAM | VIDEO_FILE | RTSP
    source_uri: Mapped[str] = mapped_column(String(512), default="0")
    status: Mapped[str] = mapped_column(String(32), default="OFFLINE")       # ONLINE | OFFLINE | ERROR
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time, onupdate=time.time)

    __table_args__ = (
        Index("ix_cameras_status", "status"),
    )


class ZoneModel(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"zone_{uuid.uuid4().hex[:8]}")
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    zone_type: Mapped[str] = mapped_column(String(32), default="restricted")  # restricted | warning | perimeter
    severity: Mapped[str] = mapped_column(String(32), default="HIGH")         # LOW | MEDIUM | HIGH | CRITICAL
    polygon: Mapped[list[list[float]]] = mapped_column(JSONType, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[str] = mapped_column(String(32), default="LOW", index=True)
    timestamp: Mapped[float] = mapped_column(Float, default=time.time, index=True)
    evidence_frame: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reasons: Mapped[list[str]] = mapped_column(JSONType, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)

    __table_args__ = (
        Index("ix_events_cam_time", "camera_id", "timestamp"),
        Index("ix_events_risk_time", "risk_level", "timestamp"),
    )


class AlertModel(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), default="HIGH", index=True)  # LOW | MEDIUM | HIGH | CRITICAL
    status: Mapped[str] = mapped_column(String(32), default="NEW", index=True)     # NEW | ACKNOWLEDGED | RESOLVED
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    evidence_frame: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=time.time, index=True)
    acknowledged_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolved_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    operator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time, onupdate=time.time)
