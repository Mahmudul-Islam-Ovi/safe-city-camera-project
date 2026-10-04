"""Pydantic schemas (data transfer objects) for Safe City REST & WebSocket APIs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# Camera Schemas
SourceType = Literal["WEBCAM", "VIDEO_FILE", "RTSP"]
CameraStatus = Literal["ONLINE", "OFFLINE", "ERROR"]


class CameraCreate(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    location: str = "Main Entrance"
    source_type: SourceType = "WEBCAM"
    source_uri: str = "0"


class CameraUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    source_type: SourceType | None = None
    source_uri: str | None = None
    status: CameraStatus | None = None
    is_active: bool | None = None


class CameraResponse(BaseModel):
    id: str
    name: str
    location: str
    source_type: SourceType
    source_uri: str
    status: CameraStatus
    is_active: bool
    created_at: float
    updated_at: float


# Zone Schemas
ZoneType = Literal["restricted", "warning", "perimeter", "public"]
SeverityLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class ZoneCreate(BaseModel):
    id: str | None = None
    camera_id: str
    name: str
    polygon: list[list[float]]
    zone_type: ZoneType = "restricted"
    severity: SeverityLevel = "HIGH"
    enabled: bool = True


class ZoneUpdate(BaseModel):
    name: str | None = None
    polygon: list[list[float]] | None = None
    zone_type: ZoneType | None = None
    severity: SeverityLevel | None = None
    enabled: bool | None = None


class ZoneResponse(BaseModel):
    id: str
    camera_id: str
    name: str
    polygon: list[list[float]]
    zone_type: ZoneType
    severity: SeverityLevel
    enabled: bool
    created_at: float


# Event Schemas
class EventCreate(BaseModel):
    camera_id: str
    event_type: str
    confidence: float
    risk_score: int
    risk_level: SeverityLevel
    track_id: int | None = None
    evidence_frame: str | None = None
    reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    camera_id: str
    track_id: int | None
    event_type: str
    confidence: float
    risk_score: int
    risk_level: str
    timestamp: float
    evidence_frame: str | None
    reasons: list[str]
    metadata_json: dict[str, Any] = Field(default_factory=dict)


# Alert Schemas
AlertStatus = Literal["NEW", "ACKNOWLEDGED", "RESOLVED"]


class AlertResponse(BaseModel):
    id: str
    event_id: str
    camera_id: str
    severity: str
    status: AlertStatus
    title: str
    description: str
    evidence_frame: str | None
    created_at: float
    acknowledged_at: float | None
    acknowledged_by: str | None
    resolved_at: float | None
    resolved_by: str | None
    operator_notes: str | None


class AlertAction(BaseModel):
    operator_name: str = "Operator"
    notes: str | None = None


# Dashboard Stats
class DashboardStats(BaseModel):
    total_cameras: int
    online_cameras: int
    people_detected: int
    active_alerts: int
    high_risk_events: int
    crowd_count: int
    events_today: int
