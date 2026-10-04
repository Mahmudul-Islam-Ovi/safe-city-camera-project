@echo off
title Safe City AI - Live Webcam Human & Object Detector
echo ======================================================================
echo          SAFE CITY AI - LIVE WEBCAM OBJECT & HUMAN DETECTOR
echo ======================================================================
echo.
echo Initializing camera feed and AI model...
echo.

set ROOT=%~dp0
set PYTHON_EXE=%ROOT%ai-engine\.venv\Scripts\python.exe

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment not found at: %PYTHON_EXE%
    echo Falling back to system python...
    set PYTHON_EXE=python
)

"%PYTHON_EXE%" "%ROOT%scripts\live_webcam_detection.py" %*

echo.
pause
