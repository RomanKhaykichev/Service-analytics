@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if exist "C:\Program Files\Docker\Docker\resources\bin\docker.exe" (
  set "PATH=C:\Program Files\Docker\Docker\resources\bin;%PATH%"
)

echo Last API logs:
docker compose -f docker-compose.local.yml --env-file .env.local logs api --tail 120
echo.
pause
endlocal
exit /b 0
