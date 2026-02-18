# Service Analytics API - Migration Script for Windows
# Usage: .\scripts\migrate.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Service Analytics API - Running Migrations" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# API directory = parent of scripts (where alembic.ini and alembic/ live)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$apiDir = (Resolve-Path (Join-Path $scriptDir "..")).Path
Set-Location $apiDir
Write-Host "Working directory: $apiDir" -ForegroundColor Gray

# Activate venv in apps/api if it exists
$venvPath = Join-Path $apiDir ".venv"
if (Test-Path $venvPath) {
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        Write-Host "Activating virtual environment..." -ForegroundColor Yellow
        & $activateScript
    }
}

# Run alembic: use venv's alembic.exe if available, else PATH; config + CWD = apiDir
$configPath = Join-Path $apiDir "alembic.ini"
$alembicExe = Join-Path $venvPath "Scripts\alembic.exe"
Write-Host "Config: $configPath" -ForegroundColor Gray
Write-Host "Running migrations..." -ForegroundColor Yellow
if (Test-Path $alembicExe) {
    & $alembicExe -c $configPath upgrade head
} else {
    alembic -c $configPath upgrade head
}

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
