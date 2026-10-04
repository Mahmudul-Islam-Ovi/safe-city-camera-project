@echo off
TITLE SAFE CITY AI — Master One-Click Runner
COLOR 0A

echo ======================================================================
echo             SAFE CITY AI — SURVEILLANCE & RISK ANALYTICS
echo ======================================================================
echo.
echo Starting Safe City AI Services:
echo   1. Backend API (FastAPI + WebSocket on Port 8000)
echo   2. AI Inference Engine (YOLO + Tracking + MJPEG on Port 8001)
echo   3. Next.js SOC Dashboard (Web on Port 3000)
echo.

REM 1. Start Backend in new window
start "Safe City — Backend API (:8000)" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM 2. Start AI Engine in new window
start "Safe City — AI Engine (:8001)" cmd /k "cd /d "%~dp0ai-engine" && .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8001"

REM 3. Start Next.js Frontend in new window
start "Safe City — SOC Dashboard (:3000)" cmd /k "cd /d "%~dp0frontend" && npm.cmd run dev"

echo.
echo All services launched!
echo.
echo Open your browser to:
echo   --^> Dashboard: http://localhost:3000/dashboard
echo   --^> API Docs:  http://localhost:8000/docs
echo   --^> AI Stream: http://localhost:8001/stream/CAM-001
echo.
echo To stop services, simply close the respective terminal windows.
echo ======================================================================
pause
