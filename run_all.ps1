# SAFE CITY AI — Master PowerShell Launcher
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "             SAFE CITY AI — SURVEILLANCE & RISK ANALYTICS             " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Launching local microservices:"
Write-Host "  -> Backend API (:8000)" -ForegroundColor Yellow
Write-Host "  -> AI Engine Vision Pipeline (:8001)" -ForegroundColor Yellow
Write-Host "  -> Next.js SOC Dashboard (:3000)" -ForegroundColor Yellow
Write-Host ""

$root = $PSScriptRoot

# Start Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# Start AI Engine
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\ai-engine'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8001"

# Start Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm.cmd run dev"

Write-Host "All processes started in separate windows." -ForegroundColor Green
Write-Host "Open: http://localhost:3000/dashboard" -ForegroundColor Cyan
