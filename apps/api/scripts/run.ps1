# Service Analytics API - Run server (Windows)
# Usage: .\scripts\run.ps1
# From repo root: .\apps\api\scripts\run.ps1

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiDir = Join-Path $scriptDir ".."
Set-Location $apiDir

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Service Analytics API - Starting server" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "API: http://127.0.0.1:8000" -ForegroundColor Yellow
Write-Host "Docs: http://127.0.0.1:8000/docs" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
