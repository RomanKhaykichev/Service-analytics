# Локальная редакция PROFiboard (Docker)

Отдельный стек: **веб + API + PostgreSQL**. Прод и обычный `docker-compose.yml` (только API + БД) не используются и не меняются.

На другом компьютере копируете **эту папку репозитория целиком** (можно переименовать в `PROFiboard`). Второй git-репозиторий не нужен.

## На целевом ПК

1. Установите [Docker Desktop](https://www.docker.com/products/docker-desktop/) для Windows (WSL 2). Перезагрузка, если установщик попросил.
2. Запустите Docker Desktop и дождитесь зелёного значка.
3. Скопируйте папку проекта, лучше без пробелов и кириллицы в пути: `C:\PROFiboard`.
4. Если Docker только что установили — **закройте PowerShell и откройте новое окно** (иначе команда `docker` может быть не в PATH).
5. В папке проекта: `.\start.bat`. Первый запуск качает образы и собирает фронт (5–15 минут). Окно не закрывайте, пока не появится `Open: http://localhost:8080`.
6. Браузер: [http://localhost:8080](http://localhost:8080).

Файлы `start.bat` / `stop.bat` только на английском (cmd на Windows ломает кириллицу). Если на том ПК старая копия — скопируйте эти два файла заново.

Остановка: `stop.bat` (данные не удаляются). Логи API: `logs-api.bat`.

Если `start.bat` пишет, что API unhealthy — замените обновлённые файлы (`start.bat`, `docker-compose.local.yml`, `apps/api/`) и снова `.\start.bat`. Том БД (`pgdata_local`) сбрасывать не нужно: миграция догонит с того места, где остановилась.

## SMS без Eskiz

Код подтверждения пишется в лог API:

```bat
docker compose -f docker-compose.local.yml --env-file .env.local logs api --tail 80
```

Ищите строку `SMS (console fallback)`.

## Что не пересекается с продом

| | Этот репозиторий как обычно | Локальная редакция |
|---|---|---|
| Файл | `docker-compose.yml` | `docker-compose.local.yml` |
| Контейнеры | `service-analytics-*` | `profiboard-local-*` |
| Volumes | `pgdata`, `api_uploads` | `pgdata_local`, `api_uploads_local` |
| Сайт | Vite / Pages / туннель | `http://localhost:8080` |
| Секреты | `.env` | `.env.local` (из `.env.local.example`) |

Можно держать оба стека на одной машине. Конфликт возможен только если занят порт **8080** (например, уже запущен `npm run dev`).

Полный сброс локальных данных (магазины, пользователи):

```bat
docker compose -f docker-compose.local.yml --env-file .env.local down -v
```
