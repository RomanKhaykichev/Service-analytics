# Исправление проблемы: manual_expenses в другой БД

## Проблема

POST /api/extra-expenses возвращает 500, потому что `app.manual_expenses` находится в другой БД, чем `fact_*` таблицы (данные загрузок).

## Диагностика

### Шаг 1: Проверка через скрипт

```bash
cd apps/api
python scripts/check_db_consistency.py
```

Скрипт покажет:
- К какой БД подключается API (из `DATABASE_URL`)
- К какой БД подключается пайплайн загрузок (из `PGHOST`/`PGPORT`/`PGDATABASE`)
- Где находятся таблицы `fact_sales` и `manual_expenses`
- Есть ли колонка `shop_id` в `manual_expenses`

### Шаг 2: Проверка через API endpoint

```bash
# Получить диагностическую информацию
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/extra-expenses/check-schema
```

Ответ покажет:
- Текущую БД и схему
- Где находятся `manual_expenses` и `fact_sales`
- Есть ли `shop_id` в `manual_expenses`

### Шаг 3: Проверка логов API

При попытке создать расход (POST /api/extra-expenses) в логах API будут диагностические сообщения:
- Текущая БД и схема
- Расположение таблиц
- Список колонок в `manual_expenses`

## Исправление

### Вариант A: Если таблицы в разных БД

1. **Убедитесь, что все используют один `DATABASE_URL`:**

   В `.env` файле (или переменных окружения):
   ```env
   DATABASE_URL=postgresql://user:password@host:port/database_name
   ```

   Для пайплайна загрузок (`import/import_batch.py`) также установите:
   ```env
   PGHOST=host
   PGPORT=port
   PGDATABASE=database_name
   PGUSER=user
   PGPASSWORD=password
   ```

   **Важно:** `PGHOST`/`PGPORT`/`PGDATABASE`/`PGUSER`/`PGPASSWORD` должны соответствовать `DATABASE_URL`.

2. **Примените миграции в правильную БД:**

   ```bash
   cd apps/api
   python -m alembic upgrade head
   ```

   Проверьте, что миграция применена:
   ```bash
   python -m alembic current
   ```

3. **Проверьте, что таблица создана:**

   ```sql
   -- Подключитесь к БД
   psql -h host -U user -d database_name
   
   -- Проверьте таблицы
   SELECT table_schema, table_name 
   FROM information_schema.tables 
   WHERE table_name IN ('manual_expenses', 'fact_sales')
   ORDER BY table_name, table_schema;
   
   -- Проверьте колонки
   SELECT column_name 
   FROM information_schema.columns 
   WHERE table_schema = 'app' AND table_name = 'manual_expenses'
   ORDER BY column_name;
   ```

### Вариант B: Если таблицы в одной БД, но разных схемах

1. **Убедитесь, что `DB_SCHEMA` одинаковый везде:**

   В `.env`:
   ```env
   DB_SCHEMA=app
   ```

2. **Проверьте, что миграции используют правильную схему:**

   В `apps/api/alembic/versions/*.py` миграции должны использовать:
   ```python
   schema='app'  # или settings.DB_SCHEMA
   ```

3. **Примените миграции:**

   ```bash
   cd apps/api
   python -m alembic upgrade head
   ```

### Вариант C: Если нужно перенести данные

**Только если `manual_expenses` уже есть в старой БД с данными:**

1. Сначала убедитесь, что схемы совпадают (миграции применены в обе БД)
2. Затем перенесите данные:

   ```sql
   -- В целевой БД (где fact_*)
   INSERT INTO app.manual_expenses (
       user_id, expense_date, amount_sum, shop_id, category, comment, created_at, updated_at
   )
   SELECT 
       user_id, expense_date, amount_sum, shop_id, category, comment, created_at, updated_at
   FROM old_database.app.manual_expenses
   WHERE is_deleted = false;
   ```

## Проверка после исправления

1. **Запустите скрипт проверки:**
   ```bash
   python apps/api/scripts/check_db_consistency.py
   ```

2. **Проверьте через API:**
   ```bash
   curl -H "Authorization: Bearer <token>" http://localhost:8000/api/extra-expenses/check-schema
   ```

3. **Попробуйте создать расход:**
   ```bash
   curl -X POST http://localhost:8000/api/extra-expenses \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "expense_date": "2026-01-23",
       "amount_sum": 1000,
       "category": "Test",
       "comment": "Test expense"
     }'
   ```

   Должен вернуть `201 Created`.

## Важные моменты

1. **НЕ копируйте таблицы вручную** - используйте миграции Alembic
2. **Всегда проверяйте**, что `DATABASE_URL` указывает на правильную БД
3. **После исправления** убедитесь, что `fact_sales` и `manual_expenses` в одной БД и схеме
4. **Логи API** теперь содержат диагностическую информацию при создании расхода

## Troubleshooting

### Ошибка "column shop_id does not exist"

Миграция не применена. Выполните:
```bash
cd apps/api
python -m alembic upgrade head
```

### Ошибка "relation does not exist"

Таблица не создана. Проверьте:
1. Применены ли миграции: `python -m alembic current`
2. Правильная ли схема: `DB_SCHEMA=app` в `.env`

### Таблицы в разных БД

Убедитесь, что:
1. `DATABASE_URL` в `.env` указывает на БД с `fact_*` таблицами
2. `PGHOST`/`PGPORT`/`PGDATABASE` соответствуют `DATABASE_URL`
3. Миграции применены: `python -m alembic upgrade head`
