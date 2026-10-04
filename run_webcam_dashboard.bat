@echo off
TITLE SAFE CITY AI — Live Webcam Web Dashboard Runner
COLOR 0B

echo ======================================================================
echo       SAFE CITY AI — LIVE WEBCAM ON WEB DASHBOARD (:3000)
echo ======================================================================
echo.
echo Configuring AI Engine to use physical WEBCAM (Camera Index 0)...
echo.

set ROOT=%~dp0
set "USE_WEBCAM=true"

REM 1. Start Backend in new window (if not already running)
start "Safe City — Backend API (:8000)" cmd /k "cd /d "%ROOT%backend" && .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

REM 2. Start AI Engine with USE_WEBCAM=true in new window
start "Safe City — AI Engine (Live Webcam :8001)" cmd /k "cd /d "%ROOT%ai-engine" && set "USE_WEBCAM=true" && .venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8001"

REM 3. Start Next.js Frontend in new window
start "Safe City — SOC Dashboard (:3000)" cmd /k "cd /d "%ROOT%frontend" && npm.cmd run dev"

echo All services launched with LIVE WEBCAM!
echo.
echo Opening browser in 3 seconds...
timeout /t 3 >nul
start http://localhost:3000/dashboard

echo.
echo Dashboard URL : http://localhost:3000/dashboard
echo Direct Stream : http://localhost:8001/stream/CAM-001
echo API Docs      : http://localhost:8000/docs
echo.
echo To stop services, close the respective command prompt windows.
echo ======================================================================
pause
