@echo off
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker не найден. Установите Docker Desktop и повторите.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop не запущен. Откройте его и дождитесь зелёного значка, затем снова start.bat.
  pause
  exit /b 1
)

if not exist ".env.local" (
  if exist ".env.local.example" (
    copy /Y ".env.local.example" ".env.local" >nul
    echo Создан файл .env.local — при желании смените пароли внутри.
  ) else (
    echo Нет .env.local.example — нечем заполнить окружение.
    pause
    exit /b 1
  )
)

echo Запуск PROFiboard ^(первый раз может занять 5–15 минут^)...
docker compose -f docker-compose.local.yml --env-file .env.local up -d --build
if errorlevel 1 (
  echo Не удалось запустить. Если порт 8080 занят, закройте другой сервер или смените WEB_PORT в .env.local.
  pause
  exit /b 1
)

echo Ожидание сайта...
timeout /t 3 /nobreak >nul
start "" "http://localhost:8080"

echo.
echo PROFiboard: http://localhost:8080
echo Код SMS ^(если Eskiz не настроен^):
echo   docker compose -f docker-compose.local.yml --env-file .env.local logs api --tail 80
echo Остановка: stop.bat
echo.
endlocal
exit /b 0
