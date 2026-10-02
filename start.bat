@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if exist "C:\Program Files\Docker\Docker\resources\bin\docker.exe" (
  set "PATH=C:\Program Files\Docker\Docker\resources\bin;%PATH%"
)

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker was not found. Install Docker Desktop, then CLOSE this window and open a new PowerShell.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not running. Start it and wait until the whale icon is idle, then run start.bat again.
  pause
  exit /b 1
)

if not exist ".env.local" (
  if exist ".env.local.example" (
    copy /Y ".env.local.example" ".env.local" >nul
    echo Created .env.local from the example file.
  ) else (
    echo Missing .env.local.example
    pause
    exit /b 1
  )
)

echo Starting database...
docker compose -f docker-compose.local.yml --env-file .env.local up -d db
if errorlevel 1 (
  echo Could not start the database.
  pause
  exit /b 1
)

set /a d=0
:waitdb
docker compose -f docker-compose.local.yml --env-file .env.local exec -T db pg_isready >nul 2>&1
if not errorlevel 1 goto dbready
set /a d+=1
if %d% GEQ 45 (
  echo Database did not become ready.
  docker compose -f docker-compose.local.yml --env-file .env.local logs db --tail 40
  pause
  exit /b 1
)
echo Waiting for database... %d%/45
timeout /t 2 /nobreak >nul
goto waitdb

:dbready
echo Adding missing columns if needed...
docker exec profiboard-local-db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'ALTER TABLE IF EXISTS app.fact_leftout_snapshot ADD COLUMN IF NOT EXISTS snap_id bigserial'"
docker exec profiboard-local-db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'ALTER TABLE IF EXISTS app.fact_leftout_snapshot ADD COLUMN IF NOT EXISTS loaded_at timestamptz NOT NULL DEFAULT now()'"
docker exec profiboard-local-db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'ALTER TABLE IF EXISTS app.fact_leftout_old_snapshot ADD COLUMN IF NOT EXISTS loaded_at timestamptz NOT NULL DEFAULT now()'"
docker exec profiboard-local-db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'ALTER TABLE IF EXISTS app.fact_leftout_old_snapshot ADD COLUMN IF NOT EXISTS fbs_qty integer NOT NULL DEFAULT 0'"
docker exec profiboard-local-db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'ALTER TABLE IF EXISTS app.fact_leftout_old_snapshot ADD COLUMN IF NOT EXISTS in_sale_qty integer NOT NULL DEFAULT 0'"
docker exec profiboard-local-db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB -c 'ALTER TABLE IF EXISTS app.fact_leftout_old_snapshot ADD COLUMN IF NOT EXISTS barcode text'"

echo Starting PROFiboard. First run can take 5-15 minutes...
docker compose -f docker-compose.local.yml --env-file .env.local up -d --build
if errorlevel 1 (
  echo Compose failed to start. Showing API logs:
  docker compose -f docker-compose.local.yml --env-file .env.local logs api --tail 80
  echo.
  echo If port 8080 is busy, close the other app or change WEB_PORT in .env.local
  pause
  exit /b 1
)

echo Waiting for API after database migrations...
set /a n=0
:waithealth
docker compose -f docker-compose.local.yml --env-file .env.local exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" >nul 2>&1
if not errorlevel 1 goto healthy
set /a n+=1
if %n% GEQ 36 goto unhealthy
echo Still starting... %n%/36
timeout /t 5 /nobreak >nul
goto waithealth

:unhealthy
echo API did not become ready. Last API logs:
docker compose -f docker-compose.local.yml --env-file .env.local logs api --tail 80
pause
exit /b 1

:healthy
echo Waiting for the site...
timeout /t 2 /nobreak >nul
start "" "http://localhost:8080"

echo.
echo Open: http://localhost:8080
echo SMS code log: logs-api.bat
echo Stop: stop.bat
echo.
pause
endlocal
exit /b 0
