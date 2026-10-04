"""Tests for FastAPI backend REST and WebSocket endpoints."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.session import Base, get_db
from app.main import app

# Test in-memory SQLite database
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def async_client():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient):
    response = await async_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "backend"


@pytest.mark.asyncio
async def test_camera_crud_flow(async_client: AsyncClient):
    # Create Camera
    payload = {
        "id": "CAM-TEST-01",
        "name": "East Gate Camera",
        "location": "Sector 4",
        "source_type": "WEBCAM",
        "source_uri": "0",
    }
    create_res = await async_client.post("/api/cameras", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["id"] == "CAM-TEST-01"
    assert created["name"] == "East Gate Camera"

    # List Cameras
    list_res = await async_client.get("/api/cameras")
    assert list_res.status_code == 200
    cams = list_res.json()
    assert len(cams) == 1
    assert cams[0]["id"] == "CAM-TEST-01"

    # Update Camera
    update_res = await async_client.put("/api/cameras/CAM-TEST-01", json={"location": "Sector 5"})
    assert update_res.status_code == 200
    assert update_res.json()["location"] == "Sector 5"


@pytest.mark.asyncio
async def test_event_ingest_and_alert_generation(async_client: AsyncClient):
    # Ingest HIGH risk event
    event_payload = {
        "camera_id": "CAM-TEST-01",
        "event_type": "restricted_zone_entry",
        "confidence": 0.94,
        "risk_score": 70,
        "risk_level": "HIGH",
        "track_id": 42,
        "reasons": ["Restricted zone entry: +30", "Running: +20", "Loitering: +20"],
    }
    ev_res = await async_client.post("/api/events", json=event_payload)
    assert ev_res.status_code == 201
    ev_data = ev_res.json()
    assert ev_data["risk_level"] == "HIGH"
    assert ev_data["track_id"] == 42

    # Check alert was automatically spawned
    alerts_res = await async_client.get("/api/alerts")
    assert alerts_res.status_code == 200
    alerts = alerts_res.json()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["severity"] == "HIGH"
    assert alert["status"] == "NEW"

    # Acknowledge alert
    ack_res = await async_client.post(f"/api/alerts/{alert['id']}/acknowledge", json={"operator_name": "Officer Smith"})
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"

    # Resolve alert
    resolve_res = await async_client.post(
        f"/api/alerts/{alert['id']}/resolve",
        json={"operator_name": "Officer Smith", "notes": "Authorized personnel confirmed"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"
