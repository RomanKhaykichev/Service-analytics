# Service Analytics API

FastAPI backend для проекта Service Analytics.

## Требования

- Python 3.11+
- PostgreSQL (локально установлен)
- PowerShell (для Windows)

## Установка и запуск (PowerShell)

```powershell
# Перейти в директорию API
cd apps/api

# Создать виртуальное окружение
python -m venv .venv

# Активировать виртуальное окружение
.\.venv\Scripts\Activate.ps1

# Установить зависимости
pip install -r requirements.txt

# Создать файл .env на основе .env.example
Copy-Item .env.example .env

# Отредактировать .env и указать правильные данные для подключения к БД
# DATABASE_URL=postgresql+psycopg2://postgres:PASSWORD@localhost:5432/service_analytics

# ⚠️ ВАЖНО: Применить миграции базы данных перед запуском!
# Windows PowerShell:
.\scripts\migrate.ps1
# Или вручную:
python -m alembic upgrade head

# Запустить сервер
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен по адресу: http://localhost:8000

## Переменные окружения

Создайте файл `.env` в директории `apps/api` на основе `.env.example`:

- `DATABASE_URL` - строка подключения к PostgreSQL (формат: `postgresql+psycopg2://user:password@host:port/database`)
- `DB_SCHEMA` - схема базы данных для таблиц и views (по умолчанию: `app`). Все SQL запросы используют эту схему через функцию `qname()`.
- `APP_ENV` - окружение приложения (`dev`/`development` для разработки, `production` для продакшена, по умолчанию: `development`)
- `DEFAULT_DEV_USER_ID` - UUID пользователя для dev-режима (используется только если `APP_ENV=dev` и заголовок `X-User-Id` отсутствует, по умолчанию: `00000000-0000-0000-0000-000000000001`)
- `LOG_LEVEL` - уровень логирования (DEBUG/INFO/WARNING/ERROR, по умолчанию: INFO)
- `JWT_SECRET` - секретный ключ для подписи JWT токенов (обязательно изменить в production)
- `JWT_ISSUER` - issuer для JWT токенов (по умолчанию: `service-analytics-api`)
- `ACCESS_TTL_MIN` - время жизни access token в минутах (по умолчанию: 15)
- `REFRESH_TTL_DAYS` - время жизни refresh token в днях (по умолчанию: 30)

## Endpoints

### Health Check
- `GET /health` - Проверка работоспособности API
  - Ответ: `{"ok": true}`

### Shops
- `GET /api/shops` - Список магазинов
  - Требует заголовок: `X-User-Id: <uuid>`

### Products
- `GET /api/products` - Список товаров с фильтрацией
  - Параметры: `period` (7d|30d|60d|90d|all), `shop_id`, `q` (поиск), `sort`, `order`, `limit`, `offset`
  - Требует заголовок: `X-User-Id: <uuid>`

### Charts
- `GET /api/charts/revenue-daily` - Дневная выручка
  - Параметры: `period`, `shop_id`
  - Требует заголовок: `X-User-Id: <uuid>` или `Authorization: Bearer <token>`
  
- `GET /api/charts/stock-current` - Текущие остатки
  - Параметры: `shop_id`, `limit`
  - Требует заголовок: `X-User-Id: <uuid>` или `Authorization: Bearer <token>`

### Debug
- `GET /debug/db` - Отладочная информация о подключении к БД и схеме
  - Показывает: текущую БД, search_path, настройку DB_SCHEMA, количество записей в views
  - Требует заголовок: `X-User-Id: <uuid>` или `Authorization: Bearer <token>`

## Примеры запросов

```powershell
# Health check (не требует заголовка)
Invoke-RestMethod -Uri http://localhost:8000/health

# Получить список магазинов (с заголовком X-User-Id)
$headers = @{ "X-User-Id" = "123e4567-e89b-12d3-a456-426614174000" }
Invoke-RestMethod -Uri http://localhost:8000/api/shops -Headers $headers

# Получить товары за последние 30 дней
Invoke-RestMethod -Uri "http://localhost:8000/api/products?period=30d" -Headers $headers

# Получить дневную выручку
Invoke-RestMethod -Uri "http://localhost:8000/api/charts/revenue-daily?period=30d" -Headers $headers

# Получить текущие остатки
Invoke-RestMethod -Uri "http://localhost:8000/api/charts/stock-current?limit=200" -Headers $headers
```

### Dev-режим (удобство разработки)

В dev-режиме (`APP_ENV=dev`) можно не передавать заголовок `X-User-Id` — будет использоваться значение из `DEFAULT_DEV_USER_ID`:

```powershell
# В dev-режиме можно вызывать без заголовка (используется DEFAULT_DEV_USER_ID)
Invoke-RestMethod -Uri http://localhost:8000/api/shops

# Или с заголовком (будет использован переданный UUID)
Invoke-RestMethod -Uri http://localhost:8000/api/shops -Headers @{ "X-User-Id" = "123e4567-e89b-12d3-a456-426614174000" }
```

**Важно:** 
- Все эндпоинты `/api/*` поддерживают два способа аутентификации:
  1. JWT Bearer token: `Authorization: Bearer <access_token>` (предпочтительно)
  2. X-User-Id header: `X-User-Id: <uuid>` (fallback для dev режима)
- В production режиме требуется один из способов аутентификации
- В dev-режиме (`APP_ENV=dev`) если оба способа отсутствуют, используется `DEFAULT_DEV_USER_ID` из `.env`
- Если заголовок присутствует, но имеет невалидный формат, вернется HTTP 401

## Настройка схемы базы данных

По умолчанию все таблицы и views находятся в схеме `app`. Это настраивается через переменную окружения `DB_SCHEMA`:

```powershell
# В .env файле
DB_SCHEMA=app
```

Все SQL запросы автоматически используют указанную схему через функцию `qname()`. Например:
- `qname("v_sales_daily")` → `app.v_sales_daily` (если `DB_SCHEMA=app`)
- `qname("v_product_current_stock")` → `app.v_product_current_stock`

Если ваши данные находятся в другой схеме, просто измените `DB_SCHEMA` в `.env` файле.

Для проверки текущей конфигурации используйте debug endpoint:
```powershell
$headers = @{ "X-User-Id" = "123e4567-e89b-12d3-a456-426614174000" }
Invoke-RestMethod -Uri http://localhost:8000/debug/db -Headers $headers
```

## Структура проекта

```
apps/api/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI приложение
│   ├── db.py            # Подключение к БД (SQLAlchemy), функция qname()
│   ├── settings.py      # Настройки из .env (включая DB_SCHEMA)
│   ├── deps.py          # Dependencies (require_user для JWT и X-User-Id)
│   ├── schemas.py       # Pydantic модели
│   ├── schemas/         # Схемы для auth
│   ├── models/          # SQLAlchemy модели (users, auth_identities, etc.)
│   ├── auth/            # Модуль аутентификации (JWT, password hashing)
│   ├── utils.py         # Вспомогательные функции
│   ├── init_db.py       # Скрипт для создания таблиц
│   └── routes/          # Роутеры
│       ├── __init__.py
│       ├── auth.py       # Аутентификация (register, login, refresh, logout, me)
│       ├── shops.py
│       ├── products.py
│       ├── charts.py
│       └── debug.py     # Debug endpoints
├── .env.example         # Пример файла с переменными окружения
├── requirements.txt     # Зависимости Python
└── README.md           # Этот файл
```

## Миграции базы данных

**⚠️ КРИТИЧЕСКИ ВАЖНО:** Перед первым запуском API необходимо применить миграции базы данных!

### Применение миграций

**Windows PowerShell:**
```powershell
.\scripts\migrate.ps1
```

**Linux/Mac:**
```bash
./scripts/migrate.sh
```

**Или вручную:**
```bash
python -m alembic upgrade head
```

### Проверка наличия таблицы

После применения миграций можно проверить наличие таблицы:

**В PostgreSQL:**
```sql
SELECT to_regclass('app.map_shop_barcode');
-- Должно вернуть: app.map_shop_barcode (не NULL)
```

**Или через Python скрипт:**
```bash
python scripts/check_db.py
```

### Проверка состояния миграций

Проверить текущую версию миграций:
```bash
python -m alembic current
```

Просмотреть историю миграций:
```bash
python -m alembic history
```

### Проверка наличия критических таблиц

Перед импортом данных рекомендуется проверить наличие критических таблиц:

```bash
python scripts/check_db.py
```

Скрипт проверит наличие следующих таблиц:
- `app.map_shop_barcode` (критически важно для импортов)
- `app.manual_expenses`
- `app.fact_sales`
- `app.fact_expenses`
- `app.dim_shop`

Если таблицы отсутствуют, скрипт выдаст ошибку и подскажет, как исправить.

### Автоматическая проверка при старте

API автоматически проверяет состояние миграций при старте и логирует:
- Текущую Alembic revision
- Наличие критических таблиц
- Предупреждения, если миграции не применены

Если миграции не применены, в логах будет видно сообщение с инструкцией по исправлению.

## Разработка

Для разработки с автоперезагрузкой при изменении кода:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API документация доступна по адресу: http://localhost:8000/docs
