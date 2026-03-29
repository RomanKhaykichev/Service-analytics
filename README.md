# Service Analytics

Монорепозиторий для проекта Service Analytics.

## Структура проекта

```
├── apps/
│   ├── web/          # Frontend (Lovable/React)
│   └── api/          # Backend API (FastAPI) - будет добавлен позже
├── docs/             # Документация
├── infra/            # Инфраструктура и деплой
└── db/               # Миграции и схемы БД
```

## Frontend (apps/web)

Frontend приложение на React + TypeScript + Vite.

### Требования

- Node.js (рекомендуется через [nvm](https://github.com/nvm-sh/nvm))
- npm

### Установка и запуск

```bash
# Перейти в директорию фронтенда
cd apps/web

# Установить зависимости
npm install

# Создать файл .env на основе .env.example
cp .env.example .env
# Или в Windows PowerShell:
# Copy-Item .env.example .env

# Заполнить переменные окружения в .env:
# VITE_SUPABASE_URL=your_supabase_url_here
# VITE_SUPABASE_PUBLISHABLE_KEY=your_supabase_publishable_key_here

# Запустить dev-сервер
npm run dev
```

Frontend будет доступен по адресу: http://localhost:8080

### Скрипты

- `npm run dev` - запуск dev-сервера
- `npm run build` - сборка для production
- `npm run lint` - проверка кода линтером
- `npm run preview` - предпросмотр production сборки

### Cloudflare Pages

Сборка на Pages выполняется через **npm** (каталог проекта: `apps/web`). Команды: `npm ci` и `npm run build`. **Bun в CI не используется** — не коммитьте `bun.lockb` в `apps/web`, иначе инструменты вроде `bun install --frozen-lockfile` могут ломать деплой.

## Backend API (apps/api)

Backend API на FastAPI размещен в `apps/api`.

### Требования

- Python 3.11+
- PostgreSQL 16

### Установка и запуск (локально)

```bash
# Перейти в директорию API
cd apps/api

# Создать виртуальное окружение
python -m venv .venv

# Активировать виртуальное окружение
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/Mac:
# source .venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
uvicorn app.main:app --reload --port 8000
```

API будет доступен по адресу: http://localhost:8000

### Endpoints

- `GET /health` - Health check endpoint

Подробная документация по текущему backend находится в [backend/README.md](backend/README.md).

## Local run with Docker

Для запуска всего стека (PostgreSQL + API) через Docker Compose:

```bash
# Создать файл .env на основе .env.example
cp .env.example .env
# Или в Windows PowerShell:
# Copy-Item .env.example .env

# Запустить все сервисы
docker compose up --build

# Или в фоновом режиме:
docker compose up --build -d
```

После запуска:

- API будет доступен по адресу: http://localhost:8000
- PostgreSQL будет доступен на порту 5432

Проверка работоспособности API:

```bash
# Windows PowerShell:
Invoke-RestMethod -Uri http://localhost:8000/health

# Или curl:
curl http://localhost:8000/health
```

Ожидаемый ответ: `{"ok": true}`

Остановка сервисов:

```bash
docker compose down
```

## Документация

Дополнительная документация находится в папке [docs/](docs/).
