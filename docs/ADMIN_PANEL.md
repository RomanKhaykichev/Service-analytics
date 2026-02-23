# Admin Panel (MVP+)

Админ-панель для владельца сервиса: мониторинг клиентов, импортов и здоровья системы.

## Созданные и изменённые файлы

### Backend (apps/api)

- **app/settings.py** — добавлена настройка `ADMIN_USER_IDS` (comma-separated emails или UUID админов).
- **app/deps.py** — добавлена зависимость `require_admin` (проверка JWT + вхождение в ADMIN_USER_IDS).
- **app/routes/admin.py** — новый роутер: overview, tenants list/detail, disable/enable, extend-trial, notes, import log/retry (retry — заглушка 501).
- **app/main.py** — подключён роутер `admin` с префиксом `/api`.
- **scripts/ensure_auth_tables.py** — добавлены колонки `upload_batch.created_at`, `updated_at`; `users.admin_notes`, `trial_ends_at`, `plan`.
- **alembic/versions/20260147_admin_upload_batch_users.py** — миграция: те же колонки для upload_batch и users.

### Frontend (apps/web)

- **src/pages/Admin.tsx** — страница `/admin`: KPI-карточки, графики (регистрации, импорты, свежесть данных), таблица тенантов с поиском, фильтром по плану, пагинацией, действиями (Disable/Enable, +7 trial, Notes).
- **src/components/layout/Sidebar.tsx** — пункт меню «Админ-панель» (Shield) с путём `/admin`.

## Запуск и проверка

### 1. Backend: миграции и переменная админа

```bash
cd apps/api
.venv\Scripts\activate   # Windows
# или: source .venv/bin/activate  # Linux/Mac

# Применить миграции (добавляет created_at в upload_batch, plan/trial_ends_at/admin_notes в users)
python -m alembic upgrade head

# Либо без Alembic — скрипт создаст/дополнит таблицы:
python scripts/ensure_auth_tables.py
```

В `.env` (или переменных окружения) задать админов (email или UUID через запятую):

```env
ADMIN_USER_IDS=admin@example.com,second-admin@example.com
```

Запуск API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend

```bash
cd apps/web
npm run dev
```

Открыть в браузере: **http://localhost:5173/admin** (или тот порт, который выводит Vite). Войти под пользователем, email которого указан в `ADMIN_USER_IDS`.

### 3. Примеры запросов curl к /api/admin/*

Получить токен (под пользователем-админом):

```bash
# Логин (подставьте свои email/password)
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your-password"}' \
  | jq -r '.access_token'
```

Сохранить токен в переменную и вызвать админ-эндпоинты:

```bash
TOKEN="<access_token_from_login>"

# Обзор (KPI + данные для графиков)
curl -s "http://localhost:8000/api/admin/overview?from=2025-01-01&to=2025-02-21" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Список тенантов (поиск, план, пагинация)
curl -s "http://localhost:8000/api/admin/tenants?search=&plan=trial&page=1&page_size=20&sort=created_at" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Детали тенанта
curl -s "http://localhost:8000/api/admin/tenants/<tenant_uuid>" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Лог импорта (batch_id = import_id)
curl -s "http://localhost:8000/api/admin/imports/<upload_batch_uuid>/log" \
  -H "Authorization: Bearer $TOKEN" | jq .

# Отключить тенанта
curl -s -X POST "http://localhost:8000/api/admin/tenants/<tenant_uuid>/disable" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" | jq .

# Включить тенанта
curl -s -X POST "http://localhost:8000/api/admin/tenants/<tenant_uuid>/enable" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" | jq .

# Продлить триал на 7 дней
curl -s -X POST "http://localhost:8000/api/admin/tenants/<tenant_uuid>/extend-trial" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"days":7}' | jq .

# Обновить заметки
curl -s -X PATCH "http://localhost:8000/api/admin/tenants/<tenant_uuid>/notes" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"notes":"Важный клиент"}' | jq .
```

Без токена или с токеном не-админа все запросы к `/api/admin/*` возвращают **403**.

## Чек-лист ручной проверки

1. **Доступ** — без `ADMIN_USER_IDS` или с пустым значением запрос к `/api/admin/overview` с любым JWT возвращает 403.
2. **Доступ** — после добавления своего email в `ADMIN_USER_IDS`, логин и запрос к `/api/admin/overview` с полученным Bearer-токеном возвращает 200 и JSON с `kpis`, `registrations_per_day`, `imports_per_day`, `data_freshness_buckets`.
3. **Страница /admin** — в браузере под админом открывается дашборд: KPI-карточки (Active MAU, Signups, Activated %, Paid/Trial/Expired, Imports 24h, Success rate), графики «Регистрации по дням» и «Импорты по дням», при наличии данных — «Свежесть данных».
4. **Таблица тенантов** — отображаются пользователи (company/email, created, plan, last import, status, freshness, imports 30d, active). Поиск по email/имени и фильтр Plan работают, пагинация «Назад/Вперёд» переключает страницы.
5. **Действия** — Disable/Enable по тенанту меняет `is_active`, после обновления списка в таблице отображается «Нет»/«Да». Кнопка «+7 trial» вызывает extend-trial и обновляет данные.
6. **Заметки** — нажатие «Edit»/текст заметки открывает диалог, сохранение отправляет PATCH `/api/admin/tenants/{id}/notes` и обновляет строку в таблице.
7. **403 на фронте** — вход под пользователем, не входящим в `ADMIN_USER_IDS`, и переход на `/admin`: отображается сообщение «Доступ запрещён» (без падения).
8. **Импорт лог** — GET `/api/admin/imports/{upload_batch_id}/log` возвращает метаданные батча (без секретов). Retry возвращает 501.
9. **Миграция** — после `alembic upgrade head` в БД есть колонки `upload_batch.created_at`, `upload_batch.updated_at`, `users.admin_notes`, `users.trial_ends_at`, `users.plan`; при их отсутствии скрипт `ensure_auth_tables.py` их добавляет.
10. **.gitignore** — в репозитории исключены `uploads/` и `*.xlsx` (уже было в .gitignore).

## Ограничения MVP

- Очередь импортов отсутствует: «Queue backlog» и «Retry import» — заглушки (0 и 501).
- Ошибки API 5xx за 24ч не пишутся в БД — в KPI возвращается `null`.
- Платежи/подписки не интегрированы: MRR, Revenue 30d, Next billing, Payment status — `null` или заглушки.
- «View tenant» (impersonate) и «View last import log» в таблице не реализованы (лог доступен по API по `import_id`).
