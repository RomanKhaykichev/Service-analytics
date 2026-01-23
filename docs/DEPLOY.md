# Deployment Guide

Полное руководство по развёртыванию Service Analytics с автоматическими миграциями Alembic.

## Быстрый старт

### Локально (одной командой)

```bash
# Запустить все сервисы (БД + API с автоматическими миграциями)
docker compose up -d --build

# Проверить статус
docker compose ps

# Посмотреть логи
docker compose logs -f api
```

### На сервере

1. **Настройте `.env` файл:**
   ```env
   DATABASE_URL=postgresql://user:password@db:5432/service_analytics
   DB_SCHEMA=app
   APP_ENV=prod
   JWT_SECRET=<strong_random_secret_min_32_chars>
   ```

2. **Запустите:**
   ```bash
   docker compose up -d --build
   ```

3. **Проверьте миграции:**
   ```bash
   docker compose logs api | grep -i migration
   ```

4. **Запустите smoke-тесты:**
   ```bash
   docker compose exec api python scripts/smoke.py
   ```

## Как это работает

### Автоматические миграции

При запуске контейнера API автоматически выполняется:

1. **Ожидание БД** — скрипт ждёт готовности PostgreSQL (до 60 секунд)
2. **Применение миграций** — `alembic upgrade head` применяет все pending миграции
3. **Запуск API** — после успешных миграций стартует uvicorn

**Entrypoint скрипт:** `apps/api/scripts/entrypoint.sh`

### Структура миграций

- **Файлы миграций:** `apps/api/alembic/versions/*.py`
- **Конфигурация:** `apps/api/alembic.ini` и `apps/api/alembic/env.py`
- **Текущая миграция:** `20260123_223716_add_shop_id_to_manual_expenses.py`

### Проверка миграций

```bash
# Текущая версия
docker compose exec api python -m alembic current

# История миграций
docker compose exec api python -m alembic history

# Применить вручную (если нужно)
docker compose exec api python -m alembic upgrade head

# Откатить одну миграцию (осторожно!)
docker compose exec api python -m alembic downgrade -1
```

## Создание новых миграций

**Важно:** Все изменения схемы БД должны быть через миграции Alembic!

```bash
# Создать новую миграцию
docker compose exec api python -m alembic revision -m "описание изменений"

# Автогенерация из моделей SQLAlchemy (если используете)
docker compose exec api python -m alembic revision --autogenerate -m "описание"
```

Затем отредактируйте созданный файл в `apps/api/alembic/versions/` и проверьте SQL.

## Резервное копирование

**Обязательно делайте backup перед миграциями в production!**

```bash
# Создать backup
docker compose exec db pg_dump -U postgres -Fc service_analytics > backup_$(date +%Y%m%d_%H%M%S).dump

# Восстановить backup
docker compose exec -T db pg_restore -U postgres -d service_analytics backup_20240101_120000.dump
```

### Автоматический backup (cron)

```bash
#!/bin/bash
# /etc/cron.daily/service-analytics-backup
BACKUP_DIR="/backups/service-analytics"
mkdir -p "$BACKUP_DIR"
cd /path/to/Service-analytics
docker compose exec -T db pg_dump -U postgres -Fc service_analytics > "$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).dump"
# Хранить последние 30 дней
find "$BACKUP_DIR" -name "backup_*.dump" -mtime +30 -delete
```

## Smoke-тесты

После деплоя проверьте работоспособность:

```bash
# Базовые тесты (без auth)
docker compose exec api python scripts/smoke.py

# С токеном (для полных тестов)
export SMOKE_TEST_TOKEN=your_jwt_token
docker compose exec api python scripts/smoke.py
```

Проверяемые endpoints:
- `GET /health` — health check
- `GET /api/shops` — список магазинов (требует auth)
- `GET /api/kpi/summary?period=30d` — KPI summary (требует auth)
- `GET /api/extra-expenses?period=30d` — доп. расходы (требует auth)

## Переменные окружения

### Обязательные

- `DATABASE_URL` — строка подключения к PostgreSQL
- `DB_SCHEMA` — схема БД (по умолчанию `app`)

### Рекомендуемые для production

- `APP_ENV=prod` — режим production
- `JWT_SECRET` — сильный секретный ключ (минимум 32 символа)
- `LOG_LEVEL=INFO` — уровень логирования

## Troubleshooting

### Миграции не применяются

1. **Проверьте логи:**
   ```bash
   docker compose logs api | grep -i migration
   ```

2. **Проверьте подключение к БД:**
   ```bash
   docker compose exec api python -c "from app.db import engine; engine.connect()"
   ```

3. **Проверьте DATABASE_URL:**
   ```bash
   docker compose exec api env | grep DATABASE_URL
   ```

4. **Проверьте схему:**
   ```bash
   docker compose exec db psql -U postgres -d service_analytics -c "SELECT * FROM app.alembic_version;"
   ```

### API не запускается

1. **Проверьте, что БД готова:**
   ```bash
   docker compose ps db
   docker compose logs db
   ```

2. **Проверьте entrypoint:**
   ```bash
   docker compose exec api cat scripts/entrypoint.sh
   ```

3. **Запустите миграции вручную:**
   ```bash
   docker compose exec api python -m alembic upgrade head
   ```

### Ошибка "column does not exist"

Это означает, что миграция не применена. Проверьте:

```bash
# Текущая версия миграции
docker compose exec api python -m alembic current

# Какие миграции есть
docker compose exec api python -m alembic history

# Применить все
docker compose exec api python -m alembic upgrade head
```

## Production Checklist

- [ ] `DATABASE_URL` настроен и указывает на production БД
- [ ] `DB_SCHEMA` совпадает со схемой в миграциях (по умолчанию `app`)
- [ ] `JWT_SECRET` — сильный случайный ключ (минимум 32 символа)
- [ ] `APP_ENV=prod` установлен
- [ ] Регулярные backups настроены (перед миграциями!)
- [ ] Firewall настроен (только необходимые порты)
- [ ] Reverse proxy настроен (Nginx/Caddy)
- [ ] HTTPS включен (Let's Encrypt)
- [ ] Smoke-тесты проходят после деплоя
- [ ] Мониторинг/логирование настроены

## Дополнительная информация

См. также:
- `README_DEPLOY.md` — полное руководство по развёртыванию
- `apps/api/alembic/README.md` — документация по миграциям (если есть)
