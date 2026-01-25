# Service Analytics API - Migration Script for Windows
# Usage: .\scripts\migrate.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Service Analytics API - Running Migrations" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Change to API directory (where alembic.ini is located)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiDir = Join-Path $scriptDir ".."
Set-Location $apiDir

# Run migrations
Write-Host "Running: python -m alembic upgrade head" -ForegroundColor Yellow
python -m alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "✅ Migrations completed successfully!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    exit 0
} else {
    Write-Host "==========================================" -ForegroundColor Red
    Write-Host "❌ Migration failed!" -ForegroundColor Red
    Write-Host "==========================================" -ForegroundColor Red
    exit 1
}
