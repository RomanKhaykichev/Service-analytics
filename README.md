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

## Backend API (apps/api)

Backend API будет размещен в `apps/api` и будет доступен по префиксу `/api`.

Подробная документация по текущему backend находится в [backend/README.md](backend/README.md).

## Документация

Дополнительная документация находится в папке [docs/](docs/).
