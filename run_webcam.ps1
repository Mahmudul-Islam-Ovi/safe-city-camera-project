# SAFE CITY AI — Live Webcam Detection Launcher
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "      SAFE CITY AI — LIVE WEBCAM OBJECT & HUMAN DETECTOR              " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting real-time webcam detector with YOLO..." -ForegroundColor Yellow
Write-Host "Controls:"
Write-Host "  [Q] or [ESC] : Quit"
Write-Host "  [S]          : Save snapshot"
Write-Host "  [P]          : Person-only toggle"
Write-Host "  [C]          : Adjust confidence"
Write-Host "  [F]          : Fullscreen toggle"
Write-Host ""

$root = $PSScriptRoot
$pythonExe = Join-Path $root "ai-engine\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Warning "Venv python not found, falling back to system python"
    $pythonExe = "python"
}

$scriptPath = Join-Path $root "scripts\live_webcam_detection.py"
& $pythonExe $scriptPath $args
