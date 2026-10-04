# SAFE CITY AI — Architecture & Roadmap

> AI-based video surveillance, object detection, tracking and **behavioral event** detection.
> This is a **decision-support prototype**. It detects *observable events* (e.g. "Restricted zone
> entry detected"), never identities or criminal intent. Serious alerts always require a human operator.

---

## A. Final Architecture

```
 ┌──────────────────────────── VIDEO SOURCES ────────────────────────────┐
 │  WebcamSource (laptop cam)   FileSource (MP4)   RTSPSource (CCTV, later)│
 └───────────────────────────────┬────────────────────────────────────────┘
                                 │  VideoSource interface (read() -> Frame)
 ┌───────────────────────────────▼──── AI ENGINE (Python, port 8001) ─────┐
 │                                                                         │
 │  CameraWorker (1 thread per camera — a failure only affects that cam)   │
 │    │                                                                    │
 │    ├─ Frame extraction  (resize, frame-skip, inference-FPS limiter)     │
 │    ├─ Detector          (Ultralytics YOLO, class filter, conf thresh)   │
 │    ├─ Tracker           (ByteTrack default / BoT-SORT optional)         │
 │    ├─ TrackStateManager (history, first/last seen, zone, activity)      │
 │    │        │                                                           │
 │    │        ├── Movement analysis  (velocity px/s, direction, state)    │
 │    │        ├── Pose analysis      (YOLO-Pose → posture → fall)         │
 │    │        ├── Zone analysis      (polygon point-in-zone)              │
 │    │        └── Scene analysis     (crowd, abandoned objects,           │
 │    │                                possible aggressive activity)       │
 │    ├─ Event Engine      (standardised Event objects + cooldowns)        │
 │    ├─ Risk Engine       (configurable rules → score, level, reasons)    │
 │    ├─ Alert generation  (threshold → alert, evidence frame, face blur)  │
 │    └─ Annotator         (boxes, IDs, labels, zones) → MJPEG stream      │
 │                                                                         │
 │  Control API (FastAPI): /health  /cameras/{id}/start|stop  /stream/{id} │
 └───────────────┬─────────────────────────────────────┬───────────────────┘
                 │ events/alerts (Redis Stream)          │ live state (Redis Pub/Sub
                 │                                       │ + camera hashes w/ TTL)
 ┌───────────────▼───────────────────────────────────────▼─────────────────┐
 │                               REDIS                                      │
 │  stream:events   channel:live   camera:{id}:state   commands channel     │
 └───────────────┬──────────────────────────────────────────────────────────┘
                 │
 ┌───────────────▼──────────────── BACKEND (FastAPI, port 8000) ───────────┐
 │  Event consumer ──► PostgreSQL (events, alerts, tracks, detections…)     │
 │  REST API: /api/cameras /api/zones /api/events /api/alerts               │
 │            /api/dashboard/stats /api/health /api/analytics/*             │
 │  WebSocket hub: /ws/events  (alerts, events, people count, cam status)   │
 │  Evidence frames served from /evidence (static, face-blurred)            │
 │  Audit log, CORS, validation, rate-limit, auth-ready                     │
 └───────────────┬──────────────────────────────────────────────────────────┘
                 │ REST + WebSocket                    ▲ MJPEG (direct from AI engine)
 ┌───────────────▼─────────────────────────────────────┴───────────────────┐
 │                 FRONTEND — Next.js SOC Dashboard (port 3000)             │
 │  /dashboard /cameras /cameras/[id] /alerts /events /zones /analytics     │
 │  /settings  — live grid, alert feed, polygon zone editor, Recharts       │
 └──────────────────────────────────────────────────────────────────────────┘
```

### Key design decisions

| Decision | Choice | Why |
|---|---|---|
| Webcam access | **AI engine opens the webcam directly** (OpenCV) and streams processed frames as MJPEG | Browser→Python frame streaming adds latency and complexity with no MVP benefit. Swapping to RTSP later only changes the `VideoSource`. |
| AI → Backend transport | **Redis Streams** for events (durable, replayable), **Pub/Sub** for high-frequency live stats | AI engine keeps running even if the backend restarts; events are not lost. Kafka can replace this later behind the same publisher interface. |
| Concurrency | One worker thread per camera, isolated `try/except` + status reporting | One camera failure → that camera `OFFLINE`, system keeps running. |
| Tracking | Ultralytics built-in ByteTrack / BoT-SORT, one tracker instance per camera | Battle-tested, no extra dependency, stable IDs. |
| Velocity | **Pixels/second only** | Real-world speed needs camera calibration (homography). Documented limitation. |
| Privacy | No face recognition, anonymous track IDs, optional face blur on evidence, raw video **not stored** by default | Privacy-by-design. |
| Config | `.env` (Pydantic Settings) + YAML/JSON in `configs/` for rules | No hardcoded thresholds or secrets. |

---

## B. Complete Folder Structure

```
safe-city-ai/
├── ai-engine/                       # Python computer-vision service
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # AI service (control API + MJPEG + camera workers)   [Ph 11/14]
│   │   ├── video_processor.py       # CLI: python -m app.video_processor --source ...     [Ph 2]
│   │   ├── config/settings.py       # Pydantic Settings (all thresholds from env)         [Ph 1]
│   │   ├── utils/                   # logging, device selection, env check, timing        [Ph 1]
│   │   ├── video/                   # VideoSource, WebcamSource, FileSource, RTSPSource   [Ph 2]
│   │   ├── detection/               # Detector (YOLO), Detection schema                   [Ph 3]
│   │   ├── tracking/                # Tracker (ByteTrack/BoT-SORT), TrackState manager    [Ph 4]
│   │   ├── activity/                # movement, loitering, crowd, abandoned, aggression   [Ph 5,7]
│   │   ├── zones/                   # polygon geometry, ZoneManager                       [Ph 6]
│   │   ├── pose/                    # PoseEstimator, posture + FallDetector               [Ph 8]
│   │   ├── risk/                    # RiskEngine (rules, levels, explanations)            [Ph 9]
│   │   ├── events/                  # Event model, EventEngine, AlertGenerator, evidence  [Ph 10]
│   │   ├── privacy/                 # optional face blurring for evidence                 [Ph 10]
│   │   ├── publishing/              # Redis publisher (events, live state)                [Ph 13]
│   │   └── pipeline/                # Pipeline orchestration, Annotator, CameraWorker     [Ph 2→]
│   ├── models/                      # YOLO weights (auto-downloaded, git-ignored)
│   ├── tests/
│   ├── requirements.txt / requirements-dev.txt / pyproject.toml / Dockerfile
│
├── backend/                         # FastAPI REST + WebSocket + persistence
│   ├── app/
│   │   ├── main.py                                                                       [Ph 11]
│   │   ├── config/settings.py                                                            [Ph 1]
│   │   ├── core/                    # logging, security, rate limiting, audit            [Ph 1/11]
│   │   ├── api/                     # routers: cameras, zones, events, alerts, dashboard  [Ph 11]
│   │   ├── models/                  # SQLAlchemy ORM models                               [Ph 12]
│   │   ├── schemas/                 # Pydantic request/response schemas                   [Ph 11]
│   │   ├── services/                # business logic, Redis consumer                      [Ph 11-13]
│   │   ├── websocket/               # connection manager + /ws/events                     [Ph 14]
│   │   └── database/                # engine/session, base                                [Ph 12]
│   ├── tests/
│   ├── requirements.txt / requirements-dev.txt / pyproject.toml / Dockerfile
│
├── frontend/                        # Next.js 15 App Router + TS + Tailwind + shadcn/ui    [Ph 15-18]
│   ├── app/ (dashboard, cameras, cameras/[id], alerts, events, zones, analytics, settings)
│   ├── components/ lib/ hooks/ types/ public/
│   └── Dockerfile, package.json
│
├── database/
│   ├── migrations/                  # Alembic migrations                                  [Ph 12]
│   └── init/                        # optional SQL bootstrap for Docker
├── configs/                         # risk_rules.yaml, demo zones, camera presets
├── videos/sample/                   # test MP4s (git-ignored except .gitkeep)
├── evidence/                        # evidence frames (git-ignored)
├── scripts/                         # helper scripts (sample video download, dev runners)
├── docs/ARCHITECTURE.md
├── docker-compose.yml                                                                    [Ph 19]
├── .env.example
├── .gitignore
└── README.md                                                                             [Ph 21]
```

---

## C. Technology Explanation

| Layer | Technology | Role in this project |
|---|---|---|
| CV | **OpenCV** | Capture (webcam/MP4/RTSP), resize, draw overlays, JPEG encode for MJPEG/evidence |
| CV | **Ultralytics YOLO (YOLO11n)** | Real-time object detection (person priority + vehicles/animals/bags) |
| CV | **YOLO11n-pose** | 17 body keypoints → posture (standing/sitting/lying) → temporal fall logic |
| CV | **ByteTrack / BoT-SORT** | Multi-object tracking, stable anonymous `track_id`s |
| CV | **PyTorch** | Inference runtime; CPU by default, CUDA optional |
| CV | **NumPy** | Geometry, velocity, polygon tests |
| API | **FastAPI + Pydantic + Uvicorn** | Typed REST API, validation, WebSocket, async |
| Data | **PostgreSQL + SQLAlchemy 2 + Alembic** | Durable storage of cameras, zones, events, alerts, audit logs; migrations |
| Realtime | **Redis** | Event stream (AI→backend), live state cache, pub/sub, camera heartbeats |
| Realtime | **WebSocket** | Push alerts/stats to dashboard instantly |
| UI | **Next.js (App Router) + TypeScript** | SOC dashboard with typed API layer |
| UI | **Tailwind + shadcn/ui** | Consistent, accessible dark UI components |
| UI | **Recharts** | Analytics charts |
| Infra | **Docker Compose** | One-command stack: postgres, redis, backend, ai-engine, frontend |

---

## D. Laptop Requirements

| | Minimum (works) | Recommended |
|---|---|---|
| OS | Windows 10/11, Ubuntu 22.04+, macOS 13+ | Windows 11 / Ubuntu 24.04 |
| CPU | 4 cores (i5 8th gen / Ryzen 5 3000) | 6–8 cores |
| RAM | 8 GB | 16 GB (Docker + Node + PyTorch) |
| Disk | 10 GB free | 20 GB (Docker images, models) |
| GPU | **Not required** | NVIDIA GTX 1650+ with CUDA 12.x (optional) |
| Camera | Built-in webcam or any USB webcam | 720p webcam |

**Expected CPU performance (YOLO11n, 640px):** ~8–20 inference FPS on a modern laptop CPU for one
camera. With pose enabled, ~5–12 FPS. The pipeline limits inference FPS (`INFERENCE_FPS`) so the UI
stays smooth. A GPU typically gives 60–150+ FPS.

---

## E. Installation Prerequisites

| Tool | Version | Needed for |
|---|---|---|
| Python | 3.11 or 3.12 | AI engine, backend |
| Node.js | 20 LTS or 22 LTS | Frontend |
| Git | any recent | Version control |
| Docker Desktop | 4.30+ | PostgreSQL + Redis (easiest on Windows), full-stack compose |
| PostgreSQL | 16 | Only if *not* using Docker |
| Redis | 7 | Only if *not* using Docker (Windows: Memurai or WSL2) |
| NVIDIA driver + CUDA 12.x | optional | GPU acceleration |

See README.md for exact per-OS commands.

---

## F. Development Roadmap

| Phase | Deliverable | Verifiable outcome |
|---|---|---|
| 1 | Scaffolding, settings, logging, env check | `python -m app.utils.check_env` passes, pytest green |
| 2 | VideoSource abstraction + frame pipeline + CLI | Webcam/MP4 window opens via CLI |
| 3 | YOLO Detector | Boxes + class + confidence on screen |
| 4 | ByteTrack tracking + TrackState | Stable IDs on people |
| 5 | Movement analysis | stationary / walking / running labels |
| 6 | Polygon zones | Zone overlay, `restricted_zone_entry` events |
| 7 | Loitering (+ crowd, abandoned objects, aggression heuristic) | `loitering` events after N seconds |
| 8 | Pose + fall detection | `fall_detected` observation |
| 9 | Risk engine | Score, level, explanation reasons |
| 10 | Events + alerts + evidence frames (+face blur) | Evidence JPEGs written, alerts generated |
| 11 | FastAPI backend | All REST endpoints in Swagger |
| 12 | PostgreSQL + Alembic | Tables + indexes created by migration |
| 13 | Redis integration | AI → Redis → backend → DB |
| 14 | WebSocket | Live JSON messages on `/ws/events` |
| 15 | Next.js dashboard | SOC dashboard with live grid + alert feed |
| 16 | Camera management | Add/edit/start/stop cameras from UI |
| 17 | Zone management | Draw polygons over a camera frame |
| 18 | Analytics | Recharts analytics page |
| 19 | Docker | `docker compose up` brings up the stack |
| 20 | Testing | pytest + frontend tests |
| 21 | Documentation | Full README |
