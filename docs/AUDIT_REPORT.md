# Аудит репозитория Service Analytics (PROFiboard)

Контекст: SaaS-аналитика для продавцов Uzum. Excel-загрузка, storage, парсеры, нормализация в Postgres, дашборд, тарифы, админка. Домен на Cloudflare. Прод-деплоя нет. Требуется: регистрация с phone + SMS-OTP верификация (на регистрации, не обязательно как способ входа).

---

## 1) AUTH

### 1.1 Регистрация / логин, хранение сессий / JWT, middleware / guards

**Status: DONE**

**Где в коде:**
- **Регистрация:** `apps/api/app/routes/auth.py` — `POST /api/auth/register` (email, password, full_name, phone, consent_processing).
- **Логин:** `POST /api/auth/login` — email + password, выдаёт access_token, refresh_token, user; refresh_token в HttpOnly cookie (`/api/auth`).
- **JWT:** `apps/api/app/auth/jwt.py` — `create_access_token`, `create_refresh_token`, `decode_token` (HS256, issuer, exp). Настройки: `apps/api/app/settings.py` (JWT_SECRET, ACCESS_TTL_MIN, REFRESH_TTL_DAYS).
- **Refresh:** `POST /api/auth/refresh` — ротация refresh (cookie или body), новый access + refresh.
- **Logout:** `POST /api/auth/logout` — отзыв refresh по токену.
- **Guards:** `apps/api/app/deps.py` — `require_user()` (JWT Bearer или fallback X-User-Id), `require_admin()` (user из require_user + вхождение в ADMIN_USER_IDS).
- **Хранение:** `app.refresh_tokens` (token_hash, user_id, expires_at); пароли в `app.auth_identities` (argon2).

**Как проверить:**
1. Регистрация: `POST /api/auth/register` с email, password, full_name, consent_processing=true → 201, access_token, refresh_token, user.
2. Логин: `POST /api/auth/login` с email, password → 200, токены, cookie.
3. Защищённый endpoint: `GET /api/shops` без токена → 401; с `Authorization: Bearer <access_token>` → 200.
4. Refresh: без cookie, с `refresh_token` в body → 200, новые токены.

**Риски:**
- **Безопасность:** В `require_user()` fallback **X-User-Id** разрешён всегда, не только в dev. В production любой клиент может подставить `X-User-Id: <uuid>` и действовать от имени этого пользователя. Нужно в prod принимать только JWT (не принимать X-User-Id при APP_ENV=prod).

---

### 1.2 Email verification (где, как)

**Status: PARTIAL**

**Где в коде:**
- **Модель и БД:** `apps/api/app/models/verification_code.py` — `VerificationCode` (user_id, channel=EMAIL/SMS, destination, code_hash, expires_at, consumed_at). Миграции: `20260143_auth_tables.py`, `20260145_ensure_auth_tables.py` — таблица `app.verification_codes`.
- **Отправка/проверка кода:** Нет. Нет эндпоинтов вида `POST /auth/send-email-code`, `POST /auth/verify-email-code`. Нет вызова почтового сервиса при регистрации.

**Как проверить:**
- Убедиться, что таблица есть: `SELECT * FROM app.verification_codes LIMIT 1;`
- Поиск по коду: `grep -r "send.*email\|verify.*email\|VerificationCode" apps/api/app/routes/` — маршрутов нет.

**Риски:**
- Функционально email verification **нет**: инфраструктура (таблица, модель) есть, логики отправки и проверки кода — нет. Для продакшена нужно либо добавить отправку/верификацию, либо явно считать регистрацию без верификации email приемлемой.

---

## 2) TENANT ISOLATION

### 2.1 tenant_id в таблицах данных клиентов

**Status: DONE**

**Где в коде:**
- Данные привязаны к **user_id** (tenant = user): `fact_sales`, `fact_expenses`, `fact_storage_snapshot`, `fact_leftout_snapshot`, `fact_leftout_old_snapshot`, `upload_batch`, `manual_expenses`, `dim_shop`, `map_shop_barcode` и др. — везде есть колонка `user_id`. Миграции в `apps/api/alembic/versions/`.

**Как проверить:**
- `grep -r "user_id" apps/api/alembic/versions/*.py` — убедиться, что ключевые таблицы содержат user_id.
- В БД: `\d app.fact_sales` и аналог для других фактов — колонка `user_id`.

**Риски:** Нет при корректной фильтрации по user_id из auth.

---

### 2.2 Все запросы фильтруются по tenant_id (user_id) из auth context

**Status: DONE**

**Где в коде:**
- Все пользовательские маршруты используют `user_id: UUID = Depends(require_user)` и подставляют только его в запросы:
  - `shops.py`, `products.py`, `charts.py`, `kpi.py`, `filters.py`, `sales.py`, `extra_expenses.py`, `imports.py`, `debug.py` — везде в SQL фигурирует `user_id = CAST(:user_id AS uuid)` или аналог, значение из JWT/X-User-Id, не из body/path.
- Админские маршруты: `require_admin`, в path передаётся `tenant_id` — это **объект** действия админа (каким tenant управлять), не подмена своего контекста; доступ только у пользователей из ADMIN_USER_IDS.

**Как проверить:**
- Поиск по коду: во всех роутах (кроме admin) нет передачи user_id из query/body; только из Depends(require_user).

**Риски:** Нет при условии отключения X-User-Id в prod (см. п. 1.1).

---

### 2.3 Негативный тест: user A не может получить данные tenant B

**Status: NOT DONE**

**Где в коде:** Автотестов с подменой user_id/tenant_id в репозитории не найдено.

**Как проверить:**
1. Создать двух пользователей (A и B), залогиниться как A, получить access_token_A.
2. Запросить данные, которые есть только у B: например `GET /api/shops` с token A — должен быть только список магазинов A (пустой или свои).
3. Негативный сценарий (если бы был endpoint с id в path): попытка `GET /api/some-resource/{user_b_id}` с token A должна возвращать 403/404. Таких «resource by id» в пользовательских API нет — все выборки идут по текущему user_id из токена.

**Риски:** Без автоматического теста остаётся риск при рефакторинге случайно подставить user_id из request. Рекомендуется добавить тест: два пользователя, запросы от A с токеном A не должны возвращать данные B.

---

## 3) TRIAL / PAYWALL

### 3.0 Регистрация и тарифы

**При регистрации пользователь попадает на сервис с тарифом Trial.**

**Где в коде:**
- В `apps/api/app/routes/auth.py` в обработчике `POST /api/auth/register` после создания записи в `users` выполняется обновление: `trial_ends_at = now + 10 days`, `plan = COALESCE(plan, 'trial')`. Таким образом, новому пользователю выставляется план **trial** и срок действия триала 10 дней. После успешной регистрации клиент получает токены и объект пользователя; при переходе в приложение (дашборд) данные о тарифе приходят из `GET /api/auth/me` (plan, trial_ends_at, trial_days_left), и пользователь видит интерфейс с тарифом Trial (баннер с датой окончания, лимит 1 магазин, 60 дней данных).

**Тарифы в системе (по аналогии с Trial):**

| Тариф      | Значение в БД (`users.plan`) | Лимит магазинов | Ограничение данных по дням | Примечание |
|------------|------------------------------|------------------|-----------------------------|------------|
| **Trial 10** | `trial`, пусто, null         | 1                | Только последние **60 дней** от макс. даты в выгрузке (при записи в fact_sales / fact_expenses) | При регистрации по умолчанию; trial_ends_at = now + 10 дней. После истечения дней кнопка загрузки блокируется у **всех** тарифов; админ может добавлять дни **любому** тарифу (extend-trial). |
| **Month 5**  | `month 5`, `month_5`, `month5` | 5                | Нет (все загруженные данные) | Платный. По правилу при оплате даётся **30 дней доступа** (см. ниже). Админ может продлевать дни через extend-trial. |
| **Month 10** | `month 10`, `month_10`, `month10` | 10               | Нет                         | Платный; при оплате по правилу — **30 дней доступа**. Админ может продлевать дни через extend-trial. |
| **Gold**     | `gold`, `gold_plan`          | Без лимита       | Нет                         | Платный спецтариф; при назначении из админки получает **30 дней доступа**. Админ может продлевать дни через extend-trial. |
| **Admin**    | любой plan (`users.plan` может быть любым) | Без лимита       | Без ограничения по дням/сроку | Пользователи из `ADMIN_USER_IDS` (email/UUID в env). В UI отображаются как тариф **Admin** (платиновый); в таблице пользователей для админ-аккаунтов действия скрыты. |

**Общее для всех не-админ тарифов:** при истечении срока (trial_ends_at в прошлом, т.е. trial_days_left ≤ 0) кнопка загрузки файлов блокируется (фронт: `HeaderActions.tsx`, условие `plan !== 'paid' && trial_days_left <= 0`). Для **Admin** блокировка не применяется: админ не ограничен по дням и может загружать отчёты без срока. Админ может добавлять дни любому тарифу через `POST /api/admin/tenants/{tenant_id}/extend-trial` с телом `{ "days": N }`.

**Оплата/назначение тарифов Month 5, Month 10 и Gold: 30 дней доступа.** При записи платежа (`POST /api/admin/tenants/{tenant_id}/payment`) для пользователей с выбранным планом Month 5 / Month 10 / Gold автоматически продлевается доступ: `trial_ends_at = GREATEST(COALESCE(trial_ends_at, paid_at), paid_at) + 30 days` (в `apps/api/app/routes/admin.py`). То есть при назначении тарифа админом даётся 30 дней доступа; если текущий trial_ends_at уже в будущем, новый срок = trial_ends_at + 30 дней.

### 3.0.1 Запись платежа: админ и автоматическая оплата (последние изменения)

**Сейчас настроено так:**

- **Админ вручную записывает платёж:** в админке в таблице пользователей есть кнопка «Записать платёж» (иконка купюры). В модальном окне админ вводит сумму и выбирает тариф: «Не менять тариф», «Month 5», «Month 10» или «Gold». При выборе тарифа пользователь **переводится на этот тариф** и получает **30 дней доступа** (в БД обновляются `users.plan` и `users.trial_ends_at`). Сумма сохраняется в таблице `app.user_payments` и в поле `users.paid_amount`; данные попадают в график «Аналитика подписок». Код: `apps/api/app/routes/admin.py` — `POST /api/admin/tenants/{tenant_id}/payment` (тело: `amount`, опционально `plan`: `"month_5"` / `"month_10"` / `"gold"`); фронт: `apps/web/src/pages/Admin.tsx` — кнопка, модалка с полями сумма и тариф, вызов API и обновление списка после успеха.
- При необходимости перед записью платежа в коде создаются таблица `app.user_payments` и колонки `users.paid_amount`, `users.trial_ends_at`, `users.plan` (если миграции к этой БД не применялись).

**При подключении оплаты (интеграция с платёжной системой):**

- Та же логика будет проходить **автоматически**: при успешной оплате (webhook или вызов API от платёжного провайдера) достаточно вызвать тот же сценарий — запись в `user_payments`, обновление `users.paid_amount`, установка `users.plan` и продление `users.trial_ends_at` на 30 дней. То есть текущая реализация рассчитана на то, что при подключении автоматической оплаты повторно используется та же бизнес-логика (тот же endpoint или вынесенная в общую функцию), без дублирования правил переключения тарифа и начисления 30 дней.

Логика лимитов и ограничения 60 дней: `apps/api/app/routes/imports.py` — `get_user_max_shops()` (для Admin/Gold без лимита), в `populate_facts()` — `is_trial_plan` и фильтр по 60 дням только для trial (для Admin принудительно `is_trial_plan = false`). В KPI/Charts также отключена trial-отсечка 60 дней для админов. Отображение названий тарифов на фронте: `ProfileDialog`, `ReportUploadDialog`, `Admin.tsx` (Trial 10, Month 5, Month 10, Gold, Admin).

**Как проверить:** Зарегистрировать нового пользователя → в БД `plan = 'trial'`, `trial_ends_at` через 10 дней; открыть дашборд под этим пользователем — в хедере/профиле отображается тариф Trial 10 и срок триала.

---

### 3.1 trial_started_at / trial_ends_at

**Status: PARTIAL**

**Где в коде:**
- **trial_ends_at:** есть. Миграция `20260147_admin_upload_batch_users.py` — `users.trial_ends_at` (timestamptz). При регистрации в `auth.py` выставляется `trial_ends_at = now + 10 days`, `plan = 'trial'`.
- **trial_started_at:** в основном приложении **нет**. Колонки в `app.users` нет; в старом скрипте `import/import_batch.py` есть упоминание — к текущему API не относится.

**Как проверить:**
- БД: `SELECT trial_ends_at, plan FROM app.users WHERE id = ...` после регистрации — дата через 10 дней.
- Фронт: `user.trial_ends_at`, `user.trial_days_left` в `useAuth`, отображаются в хедере и профиле.

**Риски:** Для аналитики «когда начался триал» trial_started_at можно вывести из `created_at` или добавить колонку.

---

### 3.2 Что происходит после окончания trial (какие фичи закрываются)

**Status: PARTIAL**

**Где в коде:**
- **У всех не-админ тарифов после истечения дней блокируется кнопка загрузки:** `apps/web/src/components/dashboard/HeaderActions.tsx` — `isTrialExpired = !user.is_admin && (plan !== 'paid' && trial_days_left != null && trial_days_left <= 0)`; `ReportUploadDialog` получает `disabled={isTrialExpired}`. У планов Trial, Month 5, Month 10 и Gold значение plan не равно `'paid'`, поэтому при истечении trial_ends_at (trial_days_left ≤ 0) кнопка неактивна. Для Admin блокировки по сроку нет.
- **Админ может добавлять дни всем тарифам:** `POST /api/admin/tenants/{tenant_id}/extend-trial` в `apps/api/app/routes/admin.py` — тело `{ "days": 7 }` (или любое N); обновляется `users.trial_ends_at` у любого выбранного tenant (Trial, Month 5, Month 10, Gold и т.д.). Доступ только у пользователей из `ADMIN_USER_IDS`.
- **Бэкенд:** Явной проверки trial_ends_at в маршруте импорта нет — блокировка загрузки реализована на фронте (disabled). По плану: `get_user_max_shops()` — trial 1 магазин, Month 5 → 5, Month 10 → 10, Gold/Admin → без лимита. Для Admin trial-ограничения по данным также отключены в `populate_facts()`, KPI и Charts.
- **Фронт:** Баннер об окончании триала, автооткрытие окна продления, кнопки «Продлить»/тарифы.

**Как проверить:**
1. Установить пользователю trial_ends_at в прошлом, plan = trial.
2. Залогиниться — баннер «триал закончился», окно продления; кнопка «Загрузить отчёты» неактивна.
3. Под админом: `POST /api/admin/tenants/{tenant_id}/extend-trial` с `{"days": 7}` — в ответе новый trial_ends_at; после обновления страницы кнопка загрузки снова активна.
4. Загрузка Excel с >1 магазином для trial — отклоняется (лимит магазинов).

**Риски:** Блокировка загрузки только на фронте; при прямом вызове API импорта с истёкшим триалом бэкенд не вернёт 403. Рекомендуется добавить проверку trial_ends_at в маршруте загрузки.

---

### 3.3 Тариф Trial: ограничение данных 60 днями

**Status: DONE**

**Где в коде:**
- В тарифе Trial при загрузке отчётов в факты попадают только данные за **последние 60 дней** от максимальной даты в текущей выгрузке. Реализовано при записи в БД, а не при чтении.
- `apps/api/app/routes/imports.py`, функция `populate_facts()`: для пользователя с планом trial читается `users.plan`, выставляется `is_trial_plan`. Для trial по типу отчёта (sales/expenses) считается `trial_cutoff_date` = MAX(дата) по текущему батчу в stg_sales/stg_expenses. В INSERT в `fact_sales` и `fact_expenses` добавлено условие: `date_created >= (trial_cutoff_date - interval '60 days')` (и аналог для date_written_off в расходах). То есть в факты для trial пишутся только строки за последние 60 дней от «конца» выгрузки.
- Графики и KPI читают из fact_sales/fact_expenses без отдельной фильтрации по плану — у trial-пользователя в БД уже лежат только эти 60 дней, поэтому на дашборде отображаются только они.

**Как проверить:**
1. Залогиниться под пользователем с plan = trial.
2. Загрузить отчёт продаж с датами, например, за 90 дней.
3. В БД: `SELECT MIN(date_created), MAX(date_created) FROM app.fact_sales WHERE user_id = ...` — разброс дат не более 60 дней; старые строки в fact_sales не попадают.
4. На дашборде (графики, KPI) виден только этот 60-дневный срез.

**Риски:** Нет. Ограничение применяется на этапе записи; для платных планов (`is_trial_plan = false`) фильтр по 60 дням не используется.

---

### 3.4 Единая функция проверки доступа (trial/plan)

**Status: NOT DONE**

**Где в коде:** Нет общей функции вида `check_trial_or_plan()` или `require_active_subscription()`. Проверки разнесены по коду:
- Импорт: `get_user_max_shops()` по plan.
- Фронт: отображение баннера и кнопок по `user.trial_days_left`, `user.plan`.

**Как проверить:** Поиск по `trial_ends_at`, `plan`, `get_user_max_shops` — единого места проверки нет.

**Риски:** При добавлении новых фич (экспорт, отчёты, лимиты) легко забыть проверку; логика «что разрешено после триала» размазана. Рекомендуется ввести единую функцию (например, в deps или auth) и использовать её в маршрутах и при лимитах.

---

## 4) ADMIN

### 4.1 Роль admin и защита admin routes

**Status: DONE**

**Где в коде:**
- Роль задаётся через env: `ADMIN_USER_IDS` (comma-separated email или UUID). Проверка: `apps/api/app/deps.py` — `is_user_admin()`, `require_admin()`.
- Все admin-маршруты под защитой: `_: UUID = Depends(require_admin)` в `apps/api/app/routes/admin.py` (overview, dashboard-metrics, tenants, tenant detail, disable/enable, extend-trial, payment, notes, set-password, delete tenant и т.д.).

**Как проверить:**
1. Запрос без токена: `GET /api/admin/tenants` → 401.
2. С токеном не-админа: → 403.
3. С токеном пользователя из ADMIN_USER_IDS: → 200 и список tenants.

**Риски:** Админский доступ полностью определяется ADMIN_USER_IDS; смена пароля админа или утечка JWT даёт полный доступ к админке и данным всех tenants.

---

### 4.2 Список клиентов, карточка клиента

**Status: DONE**

**Где в коде:**
- Список: `GET /api/admin/tenants` — пагинация, поиск, фильтр по plan, сортировка. Ответ: tenant_id, email, full_name, created_at, `is_admin`, plan, trial_ends_at, last_login_at, shops_count, imports_30d, failed_30d и др.
- Карточка: `GET /api/admin/tenants/{tenant_id}` — детали пользователя, plan, trial_ends_at, admin_notes, last_import_at, last_batch_id, imports_30d, failed_30d, data_freshness_days.
- **Запись платежа:** в списке у каждого клиента кнопка «Записать платёж» (иконка купюры); модальное окно — сумма и выбор тарифа (Month 5 / Month 10 / Gold). При выборе тарифа пользователь переводится на него и получает 30 дней доступа. API: `POST /api/admin/tenants/{tenant_id}/payment` (body: `amount`, опционально `plan`: `month_5` / `month_10` / `gold`). Для строк пользователей с `is_admin=true` кнопки действий в таблице скрыты (нет disable/enable/extend/payment/notes/password/delete).

**Как проверить:** Открыть админку в браузере (под админом), список и клик по клиенту — карточка с деталями; нажать «Записать платёж», ввести сумму и тариф — после успеха в таблице обновятся план и остаток дней.

**Риски:** Нет дополнительных.

---

### 4.3 История upload и ошибки парсинга

**Status: PARTIAL**

**Где в коде:**
- В карточке tenant есть: last_import_at, last_batch_id, статус последнего батча (success/failed), imports_30d, failed_30d. Таблицы: `upload_batch`, при наличии — `import_file_attempts` (ошибки по файлам).
- В overview/дашборде админки: агрегаты по upload_batch, top_import_error_types (если есть таблица с ошибками).
- Отдельного «полного лога загрузок по tenant» с постраничным списком батчей и ошибок в ответе API может не быть — нужно уточнить по коду (есть ли GET с историей батчей по tenant_id).

**Как проверить:** Открыть карточку tenant в админке — видна ли последняя загрузка и счётчики; проверить, есть ли endpoint с историей батчей/ошибок.

**Риски:** Если нужна детальная история (каждый батч + ошибки парсинга), может потребоваться отдельный endpoint или расширение ответа карточки.

---

## 5) PROD DEPLOY

### 5.1 Docker/compose, env, миграции, запуск воркеров очереди

**Status: PARTIAL**

**Где в коде:**
- **Docker:** `docker-compose.yml` в корне — сервисы `db` (Postgres 16), `api` (FastAPI из `apps/api/Dockerfile`). Нет отдельного сервиса frontend и нет воркеров очереди.
- **Env:** `.env.example` в корне, `apps/api/.env.example` — DATABASE_URL, DB_SCHEMA, APP_ENV, JWT_SECRET, ADMIN_USER_IDS и др.
- **Миграции:** При старте API в Docker миграции не запускаются из compose (нет команды `alembic upgrade head` в entrypoint в текущем compose). Отдельно: `apps/api/scripts/entrypoint.sh` (если есть) или ручной запуск миграций.
- **Очередь:** Импорт выполняется синхронно в HTTP-запросе (`apps/api/app/routes/imports.py`). Отдельной очереди (Celery, RQ и т.п.) и воркеров нет.

**Как проверить:**
1. `docker compose up -d --build` — поднимаются db и api.
2. `docker compose exec api python -m alembic current` — при необходимости вручную применить миграции.
3. Поиск по "celery", "worker", "queue" — отсутствуют.

**Риски:** Прод-деплой не описан пошагово (см. docs/PRODUCTION_CHECKLIST.md, README_DEPLOY.md). Большие загрузки блокируют запрос; при росте нагрузки потребуется вынос импорта в фоновые воркеры.

---

### 5.2 Конфиг для prod (логирование, secrets)

**Status: PARTIAL**

**Где в коде:**
- Логирование: `LOG_LEVEL` в settings; в коде используется стандартный `logging`. Нет структурированного JSON-логирования и единого формата для prod.
- Secrets: JWT_SECRET, пароли БД — из env; в коде не хардкодятся. В prod нужно задать переменные при деплое (документация есть в docs).

**Как проверить:** Проверить отсутствие секретов в репозитории; убедиться, что в prod заданы APP_ENV=prod, сильный JWT_SECRET, надёжный пароль БД.

**Риски:** В prod желательно явно отключить X-User-Id (см. п. 1.1), включить HTTPS, ограничить CORS; логирование для отладки инцидентов лучше унифицировать (уровень, формат).

---

## 6) SMS PHONE VERIFICATION

### 6.1 Провайдер / интеграция (Play Mobile, Eskiz и т.д.)

**Status: NOT DONE**

**Где в коде:** Интеграций с SMS-провайдерами нет. В `docs/auth_plan.md` описан план: отправка SMS, хранение OTP в `verification_codes`. Модель `VerificationCode` уже поддерживает `channel=SMS`, таблица создана миграциями.

**Как проверить:** Поиск по "sms", "eskiz", "play.mobile", "twilio" в apps/api — пусто (кроме модели и плана).

**Риски:** Без реализации регистрация с проверкой телефона через SMS недоступна.

---

### 6.2 Рекомендация: провайдер-агностик (SmsProvider + Play Mobile / Eskiz)

**Status: NOT DONE**

Реализации нет. Рекомендуемая схема:

- **Интерфейс:** например, `apps/api/app/sms/provider.py` — абстрактный класс `SmsProvider` с методом `send_sms(phone: str, text: str) -> bool`.
- **Реализации:** `PlayMobileSmsProvider`, `EskizSmsProvider` (конфиг URL, токен из env), выбор провайдера через env (например, `SMS_PROVIDER=eskiz`).
- **Эндпоинты:** `POST /api/auth/send-otp` (телефон в body, создание записи в verification_codes, отправка SMS, rate limit по phone/IP). `POST /api/auth/verify-otp` (phone + code → проверка, при регистрации — установка phone_verified_at или привязка к пользователю).

**Где хранить:** В тех же маршрутах auth или отдельный модуль `app/routes/phone_verify.py`; использование `VerificationCode` с channel=SMS, destination=phone, code_hash, expires_at (TTL 5–10 мин).

**Риски:** Без rate limit и TTL — брутфорс и спам; без хеширования кода в БД — утечка БД раскрывает коды.

---

### 6.3 Endpoints POST /auth/send-otp, POST /auth/verify-otp

**Status: NOT DONE**

**Где в коде:** Таких маршрутов в `apps/api/app/routes/auth.py` нет.

**Как проверить:** `grep -r "send-otp\|verify-otp" apps/api/` — пусто.

**Риски:** Невозможно пройти сценарий «ввод телефона → SMS с кодом → ввод кода → верификация».

---

### 6.4 Хранение OTP (TTL), rate limit, защита от брутфорса

**Status: NOT DONE**

**Где в коде:** Таблица `verification_codes` подходит для хранения (expires_at = TTL). Отдельной логики rate limit (по phone, по IP) и лимитов на попытки ввода кода нет.

**Как проверить:** Нет эндпоинтов OTP — нечего проверять. После добавления — проверить: не более N запросов send-otp на номер/IP в минуту; не более M попыток verify на один код или на номер.

**Риски:** Без ограничений — спам SMS и перебор кодов.

---

### 6.5 Поля в БД: phone, phone_verified_at

**Status: PARTIAL**

**Где в коде:** В `app.users` есть колонка `phone` (миграции/auth). Поля **phone_verified_at** в модели User и в миграциях основного приложения не найдено.

**Как проверить:** `\d app.users` — есть phone; проверить наличие phone_verified_at (или аналога) в миграциях и модели.

**Риски:** Для явной отметки «телефон подтверждён» нужно добавить phone_verified_at (timestamptz) и выставлять при успешном verify-otp.

---

## Сводная таблица статусов

| Область              | Пункт                          | Status   |
|----------------------|---------------------------------|----------|
| **AUTH**             | Регистрация/логин, JWT, guards  | DONE     |
| **AUTH**             | Email verification             | PARTIAL  |
| **TENANT ISOLATION** | tenant_id в таблицах           | DONE     |
| **TENANT ISOLATION** | Фильтрация по auth context     | DONE     |
| **TENANT ISOLATION** | Негативный тест A vs B         | NOT DONE |
| **TRIAL/PAYWALL**    | Регистрация → тариф Trial; описание тарифов (Trial 10, Month 5, Month 10, Gold, Admin) | DONE     |
| **TRIAL/PAYWALL**    | trial_ends_at                  | DONE     |
| **TRIAL/PAYWALL**    | trial_started_at               | PARTIAL  |
| **TRIAL/PAYWALL**    | После истечения: кнопка загрузки неактивна; админ может продлевать дни любому тарифу (extend-trial) | DONE     |
| **TRIAL/PAYWALL**    | Trial: данные только 60 дней (при записи в fact_*) | DONE     |
| **TRIAL/PAYWALL**    | Единая функция проверки        | NOT DONE |
| **ADMIN**            | Роль и защита routes           | DONE     |
| **ADMIN**            | Список/карточка клиентов       | DONE     |
| **ADMIN**            | Запись платежа (кнопка «Записать платёж», тариф + 30 дней); при подключении оплаты — та же логика автоматически | DONE     |
| **ADMIN**            | История upload и ошибки        | PARTIAL  |
| **PROD DEPLOY**      | Docker, env, миграции          | PARTIAL  |
| **PROD DEPLOY**      | Воркеры очереди                | NOT DONE |
| **PROD DEPLOY**      | Конфиг prod (логи, secrets)    | PARTIAL  |
| **SMS**              | Провайдер/интеграция           | NOT DONE |
| **SMS**              | send-otp / verify-otp          | NOT DONE |
| **SMS**              | OTP TTL, rate limit           | NOT DONE |
| **SMS**              | phone_verified_at в БД         | PARTIAL  |

---

## Топ-10 задач на ближайшие 10 дней (в порядке приоритета)

1. **Prod: отключить X-User-Id**  
   В `deps.require_user()` при `APP_ENV=prod` не принимать заголовок X-User-Id; только JWT. Критично для безопасности.

2. **SMS: добавить phone_verified_at**  
   Миграция: колонка `app.users.phone_verified_at` (timestamptz, nullable). Обновить модель/схемы при необходимости.

3. **SMS: интерфейс SmsProvider + Eskiz (или Play Mobile)**  
   Модуль `app/sms/provider.py` с абстракцией и одной реализацией; выбор через env; отправка текста на номер.

4. **SMS: POST /auth/send-otp и POST /auth/verify-otp**  
   send-otp: генерация кода, сохранение в verification_codes (channel=SMS, hash, expires_at 5–10 мин), вызов SmsProvider, rate limit по phone (и при возможности по IP). verify-otp: проверка кода, установка phone_verified_at для пользователя (при регистрации — привязка к только что созданному user или к существующему по phone).

5. **SMS: rate limit и защита от брутфорса**  
   Ограничение запросов send-otp (например, 3–5 в 15 мин на номер); ограничение попыток verify на один код или на номер (например, 5 попыток).

6. **Регистрация: привязка SMS-верификации**  
   Сценарий: после ввода email/password/phone — вызов send-otp; на следующем шаге ввод кода и verify-otp; при успехе завершение регистрации и установка phone_verified_at. Опционально: не считать регистрацию завершённой без верификации телефона (по продукту).

7. **Trial: единая функция проверки доступа**  
   В deps или отдельном модуле: например, `get_subscription_status(user_id) -> (allowed: bool, reason: str)` с учётом trial_ends_at и plan. Использовать в импорте (лимит магазинов) и при добавлении новых платных фич (при необходимости — блокировка дашборда/экспорта после триала).

8. **Тест изоляции tenant**  
   Автотест: два пользователя A и B; запросы от A (с JWT A) к API данных не возвращают данные B; при попытке доступа по id B (если появится такой endpoint) — 403/404.

9. **Email verification (минимальный вариант)**  
   Либо явно объявить «без email verification», либо добавить отправку кода при регистрации и эндпоинт verify-email-code с записью в verification_codes (channel=EMAIL) и флагом email_verified (или аналог в users).

10. **Prod: зафиксировать деплой и миграции**  
    В docker-compose или entrypoint API явно запускать `alembic upgrade head` при старте (или документировать обязательный шаг); проверить деплой по docs/PRODUCTION_CHECKLIST.md; при необходимости добавить структурированное логирование для prod.
