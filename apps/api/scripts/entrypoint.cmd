@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Service Analytics API - Starting...
echo ==========================================

REM Wait for database to be ready (with retry)
echo Waiting for database to be ready...
set RETRIES=30

:wait_db
python -c "import psycopg2; psycopg2.connect('%DATABASE_URL%')" 2>nul
if %ERRORLEVEL% EQU 0 goto db_ready

if %RETRIES% EQU 0 (
    echo ERROR: Database is not available after 60 seconds
    exit /b 1
)

echo Waiting for database... %RETRIES% retries left
set /a RETRIES-=1
timeout /t 2 /nobreak >nul
goto wait_db

:db_ready
echo Database is ready!

REM Run migrations
echo ==========================================
echo Running Alembic migrations...
echo ==========================================
cd /d %~dp0\..
python -m alembic upgrade head

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Migration failed!
    exit /b 1
)

echo Migrations completed successfully!

REM Start the API
echo ==========================================
echo Starting API server...
echo ==========================================
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
