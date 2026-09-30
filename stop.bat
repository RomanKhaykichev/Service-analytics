@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker не найден.
  pause
  exit /b 1
)

if exist ".env.local" (
  docker compose -f docker-compose.local.yml --env-file .env.local stop
) else (
  docker compose -f docker-compose.local.yml stop
)

if errorlevel 1 (
  echo Не удалось остановить контейнеры.
  pause
  exit /b 1
)

echo PROFiboard остановлен. Данные в Docker сохранились. Снова: start.bat
endlocal
exit /b 0
