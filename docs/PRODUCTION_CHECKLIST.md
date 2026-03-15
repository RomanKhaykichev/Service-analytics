# Подготовка сервиса к продакшену

Краткий чеклист и шаги для вывода profiboard.uz (или своего домена) в production.

---

## 1. Backend (API)

### 1.1. Переменные окружения

Создайте `.env` в корне проекта (или в `apps/api` при запуске без Docker), на основе `apps/api/.env.example`:

```env
# Обязательно поменять в продакшене
DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/service_analytics
DB_SCHEMA=app
APP_ENV=prod
JWT_SECRET=<случайная_строка_минимум_32_символа>

# Админка: email или UUID через запятую
ADMIN_USER_IDS=admin@example.com

# Опционально
LOG_LEVEL=INFO
```

- **JWT_SECRET** — сгенерируйте надёжный ключ (например: `openssl rand -base64 32`).
- **DATABASE_URL** — в Docker используйте хост `db` и пароль из `.env`.
- **ADMIN_USER_IDS** — только эти пользователи имеют доступ к `/api/admin/*`.

### 1.2. Миграции БД

Перед первым запуском в production примените миграции:

```bash
cd apps/api
python -m alembic upgrade head
```

В Docker миграции часто выполняются из entrypoint при старте контейнера — проверьте логи: `docker compose logs api | grep -i migration`.

### 1.3. Резервная копия перед обновлениями

Перед каждым деплоем и миграциями делайте бэкап:

```bash
# Локальная БД
pg_dump -U postgres -Fc service_analytics > backup_$(date +%Y%m%d).dump

# Через Docker
docker compose exec -T db pg_dump -U postgres -Fc service_analytics > backup_$(date +%Y%m%d).dump
```

---

## 2. Frontend (React/Vite)

### 2.1. URL API при сборке

Если API на поддомене (например `https://api.profiboard.uz`), при сборке задайте:

**PowerShell (Windows):**
```powershell
cd apps/web
$env:VITE_API_URL = "https://api.profiboard.uz"; npm run build
```

**Bash (Linux/macOS):**
```bash
cd apps/web
VITE_API_URL=https://api.profiboard.uz npm run build
```

Либо создайте `apps/web/.env.production`:
```env
VITE_API_URL=https://api.profiboard.uz
```

После этого `npm run build` будет использовать этот URL для всех запросов к API (включая трекинг лендинга и «Попробовать бесплатно»).

### 2.2. Supabase (если используется)

В `apps/web` задайте в `.env.production` или при сборке:

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

Значения возьмите из панели Supabase для продакшен-проекта.

### 2.3. Сборка и раздача статики

```bash
cd apps/web
npm ci
npm run build
```

Папка `dist/` — статические файлы. Раздавайте их через:

- **Nginx/Apache** — корень сайта = `dist/`, для SPA настройте fallback на `index.html` для всех путей.
- **Node (serve):** `npx serve -s dist -l 8080` (флаг `-s` даёт fallback для React Router).
- **Cloudflare Tunnel** — укажите в конфиге туннеля сервис на порт, где слушает статика (например 8080).

---

## 3. Инфраструктура

### Вариант A: Cloudflare Tunnel (без VPS, без белого IP)

Подходит, когда БД и приложение работают на одной машине (например, домашний ПК или сервер в офисе).

1. Установите **cloudflared** и выполните `cloudflared tunnel login`.
2. Создайте туннель: `cloudflared tunnel create profiboard`.
3. Привяжите DNS: `profiboard.uz`, `www.profiboard.uz`, `api.profiboard.uz` через `cloudflared tunnel route dns profiboard ...`.
4. Настройте `deploy/cloudflared-config.yml`: подставьте **Tunnel ID** и путь к **credentials-file**.
5. Запустите фронт (или статику на 8080), API на 8000, затем туннель:  
   `cloudflared tunnel --config deploy/cloudflared-config.yml run profiboard`.

Подробно: **docs/CLOUDFLARE_TUNNEL_SETUP.md**.

### Вариант B: VPS (Docker)

1. Установите Docker и Docker Compose на сервере.
2. Клонируйте репозиторий, создайте `.env` из `.env.example` в корне.
3. Для production в `.env`: `APP_ENV=prod`, надёжный `POSTGRES_PASSWORD` и `JWT_SECRET`.
4. Запуск: `docker compose up -d --build`.
5. Настройте Nginx (или Caddy) как reverse proxy с HTTPS (Let's Encrypt) для фронта и API.

Подробно: **README_DEPLOY.md**, **docs/DEPLOY.md**.

---

## 4. CORS

В **`apps/api/app/main.py`** в `CORSMiddleware` уже добавлены:

- `https://profiboard.uz`
- `https://www.profiboard.uz`

Если фронт будет на другом домене — добавьте его в `allow_origins`.

---

## 5. Проверка после деплоя

- [ ] **API:** `curl -s https://api.profiboard.uz/health` → `{"ok":true}`  
- [ ] **API docs:** открыть `https://api.profiboard.uz/docs`  
- [ ] **Фронт:** открыть https://profiboard.uz, проверить логин и загрузку данных  
- [ ] **Сеть:** в DevTools → Network убедиться, что запросы к API идут на `https://api.profiboard.uz` и без ошибок  
- [ ] **Трекинг:** зайти на лендинг, нажать «Попробовать бесплатно» — в админке должны обновиться метрики воронки (если API и фронт настроены и миграции с `landing_visits`/`promo_try_clicks` применены)  
- [ ] **Админка:** вход под пользователем из `ADMIN_USER_IDS`, доступ к `/admin`

---

## 6. Чеклист перед продакшеном

| Шаг | Действие |
|-----|----------|
| 1 | Задать в API: `APP_ENV=prod`, надёжный `JWT_SECRET`, корректный `DATABASE_URL` и `ADMIN_USER_IDS` |
| 2 | Применить миграции: `alembic upgrade head` (или проверить автоматический запуск в Docker) |
| 3 | Собрать фронт с `VITE_API_URL=https://api.profiboard.uz` (или своим URL API) |
| 4 | Настроить раздачу статики фронта и прокси/туннель для API |
| 5 | Включить HTTPS (Cloudflare или Let's Encrypt) |
| 6 | Настроить регулярные бэкапы БД |
| 7 | Прогнать проверки из раздела 5 |

---

## Полезные ссылки

- **README_DEPLOY.md** — развёртывание через Docker, миграции, бэкапы  
- **docs/DEPLOY.md** — миграции, переменные, smoke-тесты  
- **docs/CLOUDFLARE_TUNNEL_SETUP.md** — пошаговая настройка Cloudflare Tunnel для profiboard.uz  
