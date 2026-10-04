"""REST API routers for Safe City AI Backend:
- /api/cameras
- /api/zones
- /api/events
- /api/alerts
- /api/dashboard/stats
- /api/health
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.entities import AlertModel, Camera, EventModel, ZoneModel
from app.schemas.contracts import (
    AlertAction,
    AlertResponse,
    CameraCreate,
    CameraResponse,
    CameraUpdate,
    DashboardStats,
    EventCreate,
    EventResponse,
    ZoneCreate,
    ZoneResponse,
    ZoneUpdate,
)
from app.websocket.manager import ws_manager

router = APIRouter()


# ------------------ Health ------------------
@router.get("/health")
async def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "service": "backend",
        "timestamp": time.time(),
    }


# ------------------ Cameras ------------------
@router.get("/cameras", response_model=list[CameraResponse])
async def list_cameras(db: AsyncSession = Depends(get_db)) -> list[Camera]:
    result = await db.execute(select(Camera).order_by(Camera.id))
    return list(result.scalars().all())


@router.post("/cameras", response_model=CameraResponse, status_code=201)
async def create_camera(payload: CameraCreate, db: AsyncSession = Depends(get_db)) -> Camera:
    existing = await db.get(Camera, payload.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Camera with ID {payload.id} already exists")

    cam = Camera(
        id=payload.id,
        name=payload.name,
        location=payload.location,
        source_type=payload.source_type,
        source_uri=payload.source_uri,
        status="ONLINE",
    )
    db.add(cam)
    await db.commit()
    await db.refresh(cam)
    return cam


@router.get("/cameras/{camera_id}", response_model=CameraResponse)
async def get_camera(camera_id: str, db: AsyncSession = Depends(get_db)) -> Camera:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam


@router.put("/cameras/{camera_id}", response_model=CameraResponse)
async def update_camera(camera_id: str, payload: CameraUpdate, db: AsyncSession = Depends(get_db)) -> Camera:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(cam, field, val)

    await db.commit()
    await db.refresh(cam)
    return cam


@router.delete("/cameras/{camera_id}", status_code=204)
async def delete_camera(camera_id: str, db: AsyncSession = Depends(get_db)) -> None:
    cam = await db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    await db.delete(cam)
    await db.commit()


# ------------------ Zones ------------------
@router.get("/zones", response_model=list[ZoneResponse])
async def list_zones(camera_id: str | None = None, db: AsyncSession = Depends(get_db)) -> list[ZoneModel]:
    stmt = select(ZoneModel)
    if camera_id:
        stmt = stmt.where(ZoneModel.camera_id == camera_id)
    result = await db.execute(stmt.order_by(ZoneModel.created_at.desc()))
    return list(result.scalars().all())


@router.post("/zones", response_model=ZoneResponse, status_code=201)
async def create_zone(payload: ZoneCreate, db: AsyncSession = Depends(get_db)) -> ZoneModel:
    zone = ZoneModel(
        id=payload.id or f"zone_{int(time.time()*1000)%100000}",
        camera_id=payload.camera_id,
        name=payload.name,
        polygon=payload.polygon,
        zone_type=payload.zone_type,
        severity=payload.severity,
        enabled=payload.enabled,
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


@router.put("/zones/{zone_id}", response_model=ZoneResponse)
async def update_zone(zone_id: str, payload: ZoneUpdate, db: AsyncSession = Depends(get_db)) -> ZoneModel:
    zone = await db.get(ZoneModel, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(zone, field, val)

    await db.commit()
    await db.refresh(zone)
    return zone


@router.delete("/zones/{zone_id}", status_code=204)
async def delete_zone(zone_id: str, db: AsyncSession = Depends(get_db)) -> None:
    zone = await db.get(ZoneModel, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    await db.delete(zone)
    await db.commit()


# ------------------ Events ------------------
@router.get("/events", response_model=list[EventResponse])
async def list_events(
    camera_id: str | None = None,
    risk_level: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[EventModel]:
    stmt = select(EventModel)
    if camera_id:
        stmt = stmt.where(EventModel.camera_id == camera_id)
    if risk_level:
        stmt = stmt.where(EventModel.risk_level == risk_level)
    result = await db.execute(stmt.order_by(EventModel.timestamp.desc()).limit(limit))
    return list(result.scalars().all())


@router.post("/events", response_model=EventResponse, status_code=201)
async def ingest_event(payload: EventCreate, db: AsyncSession = Depends(get_db)) -> EventModel:
    """Ingest event from AI Engine, automatically create Alert if MEDIUM/HIGH/CRITICAL, and broadcast."""
    ev = EventModel(
        camera_id=payload.camera_id,
        track_id=payload.track_id,
        event_type=payload.event_type,
        confidence=payload.confidence,
        risk_score=payload.risk_score,
        risk_level=payload.risk_level,
        evidence_frame=payload.evidence_frame,
        reasons=payload.reasons,
        metadata_json=payload.metadata,
    )
    db.add(ev)
    await db.flush()

    # Automatically generate alert if risk is above LOW
    alert_created = None
    if payload.risk_level in ("MEDIUM", "HIGH", "CRITICAL"):
        reasons_str = ", ".join(ev.reasons)
        description = f"Risk Score {ev.risk_score} ({ev.risk_level}) on {ev.camera_id}. Reasons: {reasons_str}"
        title = f"{ev.event_type.replace('_', ' ').capitalize()} Detected"
        alert = AlertModel(
            event_id=ev.id,
            camera_id=ev.camera_id,
            severity=ev.risk_level,
            title=title,
            description=description,
            evidence_frame=ev.evidence_frame,
            status="NEW",
        )
        db.add(alert)
        await db.flush()
        alert_created = alert

    await db.commit()
    await db.refresh(ev)

    # Broadcast via WebSocket to dashboard
    broadcast_msg: dict[str, Any] = {
        "type": "event",
        "event": {
            "id": ev.id,
            "camera_id": ev.camera_id,
            "event_type": ev.event_type,
            "risk_score": ev.risk_score,
            "risk_level": ev.risk_level,
            "timestamp": ev.timestamp,
            "evidence_frame": ev.evidence_frame,
            "reasons": ev.reasons,
        },
    }
    if alert_created:
        broadcast_msg["alert"] = {
            "id": alert_created.id,
            "severity": alert_created.severity,
            "title": alert_created.title,
            "description": alert_created.description,
            "status": alert_created.status,
            "timestamp": alert_created.created_at,
        }

    await ws_manager.broadcast(broadcast_msg)
    return ev


# ------------------ Alerts ------------------
@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> list[AlertModel]:
    stmt = select(AlertModel)
    if status:
        stmt = stmt.where(AlertModel.status == status)
    result = await db.execute(stmt.order_by(AlertModel.created_at.desc()).limit(limit))
    return list(result.scalars().all())


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    action: AlertAction,
    db: AsyncSession = Depends(get_db),
) -> AlertModel:
    alert = await db.get(AlertModel, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = time.time()
    alert.acknowledged_by = action.operator_name
    if action.notes:
        alert.operator_notes = action.notes

    await db.commit()
    await db.refresh(alert)

    # Broadcast update
    await ws_manager.broadcast({
        "type": "alert_update",
        "alert_id": alert.id,
        "status": "ACKNOWLEDGED",
        "operator": action.operator_name,
    })
    return alert


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    action: AlertAction,
    db: AsyncSession = Depends(get_db),
) -> AlertModel:
    alert = await db.get(AlertModel, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "RESOLVED"
    alert.resolved_at = time.time()
    alert.resolved_by = action.operator_name
    if action.notes:
        alert.operator_notes = f"{alert.operator_notes or ''}\n{action.notes}".strip()

    await db.commit()
    await db.refresh(alert)

    # Broadcast update
    await ws_manager.broadcast({
        "type": "alert_update",
        "alert_id": alert.id,
        "status": "RESOLVED",
        "operator": action.operator_name,
    })
    return alert


# ------------------ Dashboard Stats ------------------
@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> DashboardStats:
    total_cams = (await db.execute(select(func.count(Camera.id)))).scalar() or 0
    online_cams = (await db.execute(select(func.count(Camera.id)).where(Camera.status == "ONLINE"))).scalar() or 0
    new_alerts_stmt = select(func.count(AlertModel.id)).where(AlertModel.status == "NEW")
    active_alerts = (await db.execute(new_alerts_stmt)).scalar() or 0
    high_risk_events = (
        await db.execute(
            select(func.count(EventModel.id)).where(EventModel.risk_level.in_(["HIGH", "CRITICAL"]))
        )
    ).scalar() or 0
    total_events = (await db.execute(select(func.count(EventModel.id)))).scalar() or 0

    return DashboardStats(
        total_cameras=total_cams,
        online_cameras=online_cams,
        people_detected=0,  # updated dynamically via websocket
        active_alerts=active_alerts,
        high_risk_events=high_risk_events,
        crowd_count=0,
        events_today=total_events,
    )
