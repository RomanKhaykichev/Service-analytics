@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if exist "C:\Program Files\Docker\Docker\resources\bin\docker.exe" (
  set "PATH=C:\Program Files\Docker\Docker\resources\bin;%PATH%"
)

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker was not found.
  pause
  exit /b 1
)

if exist ".env.local" (
  docker compose -f docker-compose.local.yml --env-file .env.local stop
) else (
  docker compose -f docker-compose.local.yml stop
)

if errorlevel 1 (
  echo Failed to stop containers.
  pause
  exit /b 1
)

echo PROFiboard stopped. Data is kept. Start again with start.bat
pause
endlocal
exit /b 0
