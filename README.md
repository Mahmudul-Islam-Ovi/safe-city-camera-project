# SAFE CITY AI

**AI-Based Video Surveillance, Object Detection, Tracking and Behavioral Risk Detection System**

A privacy-conscious Safe City video analytics decision-support platform designed to process video, detect people and objects, track entities across frames with ByteTrack/BoT-SORT, detect observable behavioral events, calculate explainable risk scores, and stream real-time alerts to a Next.js Security Operations Center (SOC) dashboard.

---

## 🛡️ Core Safety & Privacy Principles

1. **Observable Events Only**:
   The system detects observable events (*"Restricted zone entry detected"*, *"Possible fall detected"*, *"Possible loitering detected"*). It **never** claims a person is a "criminal" or predicts intent.
2. **Human in the Loop**:
   All HIGH and CRITICAL alerts generate actionable tickets requiring human operator review and manual resolution.
3. **Privacy by Design**:
   - No facial recognition or biometric identification.
   - Anonymous integer Track IDs only.
   - Raw video is **not stored** by default.
   - Captured evidence frames automatically have face blurring applied.

---

## 🚀 One-Click Master Launchers (Windows)

You can launch the entire system (Backend API, AI Engine, and Frontend Web Dashboard) with **one click**:

### Method 1: Double Click
Simply double-click:
```
safe-city-ai/run_all.bat
```
*(This opens the 3 microservices in separate windows and launches the system)*

### Method 2: PowerShell
```powershell
cd "d:\starling cyber scurity\safe city project\safe-city-ai"
.\run_all.ps1
```

Once running, open your web browser:
- 🖥️ **SOC Web Dashboard**: [http://localhost:3000/dashboard](http://localhost:3000/dashboard)
- 📡 **Backend REST & WebSocket API**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 👁️ **Live Computer Vision Stream**: [http://localhost:8001/stream/CAM-001](http://localhost:8001/stream/CAM-001)

---

## 🎥 Testing Computer Vision Without CCTV

### 1. Run with Sample Surveillance MP4:
```powershell
cd ai-engine
.\.venv\Scripts\Activate.ps1
python -m app.video_processor --source ../videos/sample/test.mp4
```

### 2. Run with Laptop Webcam:
```powershell
cd ai-engine
.\.venv\Scripts\Activate.ps1
python -m app.video_processor --webcam
```

**Interactive Controls in the Video Window**:
- Press `z` to toggle the virtual Restricted Zone on/off.
- Press `q` or `ESC` to close the window.

---

## 📊 Observable Behaviors Detected

| Event | Logic | Config Key |
|---|---|---|
| **Person Detection & Tracking** | Ultralytics YOLO + ByteTrack | `CONFIDENCE_THRESHOLD=0.40` |
| **Walking / Running** | Kinematic pixel velocity over 1s trajectory window | `STATIONARY_SPEED_PX=15`, `RUNNING_SPEED_PX=180` |
| **Loitering** | Track center remains within radius for > duration | `LOITERING_TIME_SECONDS=120`, `LOITERING_RADIUS_PIXELS=100` |
| **Restricted Zone Entry** | Point-in-polygon containment test on ground contact | Defined in `ZoneManager` / Polygon UI |
| **Possible Fall** | Keypoint geometry transition: standing/sitting -> rapid posture change -> lying down | `rapid_fall_seconds=1.2` |
| **Possible Abandoned Object** | Stationary backpack/handbag without owner within 150px | `ABANDONED_OBJECT_SECONDS=60` |
| **Possible Aggressive Activity** | Proximity < 80px + sudden rapid mutual velocity | `proximity_threshold_px=80` |
| **Crowd Density** | Active person counts in camera viewport | `CROWD_THRESHOLD=20` (High), `40` (Critical) |

---

## ⚖️ Behavioral Risk Engine

Score range: **0 to 100**
- `0–29`: **LOW**
- `30–59`: **MEDIUM**
- `60–79`: **HIGH**
- `80–100`: **CRITICAL**

Configurable in `configs/risk_rules.yaml`. The system provides human-readable explanations for every score (e.g. `Restricted zone entry: +30, Running in restricted zone: +20`).

---

## 🐳 Docker Deployment

To launch all 5 containers (PostgreSQL, Redis, Backend, AI Engine, Frontend):
```bash
docker compose up --build
```
*(Requires Docker Desktop)*

---

## 🧪 Testing & Verification

Run the automated test suites for both services:

```powershell
# 1. AI Engine Test Suite (39 passed)
cd ai-engine
.\.venv\Scripts\Activate.ps1
python -m pytest

# 2. Backend Test Suite (14 passed)
cd ..\backend
.\.venv\Scripts\Activate.ps1
python -m pytest
```
