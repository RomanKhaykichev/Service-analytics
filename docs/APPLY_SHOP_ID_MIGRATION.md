# Применение миграции shop_id для manual_expenses

## Проблема

POST /api/extra-expenses возвращает 500:
```
UndefinedColumn: column "shop_id" of relation "manual_expenses" does not exist
```

## Решение

Миграция уже существует: `20260123_223716_add_shop_id_to_manual_expenses.py`

Нужно применить её в ту же БД, что использует API.

## Шаги

### Шаг 1: Диагностика (до миграции)

```bash
cd apps/api
python scripts/apply_shop_id_migration.py
```

Скрипт покажет:
- К какой БД подключён API
- Где находится таблица `manual_expenses`
- Есть ли колонка `shop_id`
- Применена ли миграция

### Шаг 2: Проверка DATABASE_URL

Убедитесь, что `DATABASE_URL` в `.env` указывает на правильную БД:

```bash
# В apps/api/.env или корневом .env
DATABASE_URL=postgresql://user:password@host:port/database_name
DB_SCHEMA=app
```

**Важно:** Это должна быть та же БД, где находятся таблицы `fact_*` (данные загрузок).

### Шаг 3: Применение миграции

```bash
cd apps/api
python -m alembic upgrade head
```

Вы должны увидеть:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 20260123_223716, add shop_id to manual_expenses
```

### Шаг 4: Проверка (после миграции)

```bash
# Снова запустите диагностический скрипт
python scripts/apply_shop_id_migration.py
```

Теперь должно показать:
- ✅ shop_id column exists: YES
- ✅ Migration applied: YES

### Шаг 5: Проверка через SQL (опционально)

```sql
-- Подключитесь к БД
psql -h host -U user -d database_name

-- Проверьте колонки
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'app' AND table_name = 'manual_expenses'
ORDER BY column_name;

-- Должна быть колонка shop_id (uuid, nullable=true)

-- Проверьте индекс
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'app'
  AND tablename = 'manual_expenses'
  AND indexname = 'ix_manual_expenses_user_shop_date';
```

### Шаг 6: Перезапуск API и тест

```bash
# Перезапустите API
# Затем проверьте POST запрос

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

## Troubleshooting

### Ошибка: "Migration already applied" но shop_id нет

Это означает, что миграция применена в другую БД.

1. Проверьте `DATABASE_URL`:
   ```bash
   # В терминале, где запускаете alembic
   echo $DATABASE_URL
   
   # В логах API при старте (должен быть тот же)
   ```

2. Убедитесь, что используете один и тот же `.env` файл

3. Примените миграцию снова:
   ```bash
   cd apps/api
   python -m alembic upgrade head
   ```

### Ошибка: "relation does not exist"

Таблица `manual_expenses` не существует. Нужно сначала создать таблицу (через другую миграцию или вручную).

### Ошибка: "schema app does not exist"

Схема `app` не существует. Создайте её:
```sql
CREATE SCHEMA IF NOT EXISTS app;
```

### Миграция не применяется

1. Проверьте логи Alembic:
   ```bash
   python -m alembic upgrade head --verbose
   ```

2. Проверьте подключение к БД:
   ```bash
   python -c "from app.db import engine; engine.connect()"
   ```

3. Проверьте, что миграция существует:
   ```bash
   ls apps/api/alembic/versions/20260123_223716*.py
   ```

## Проверка через API endpoint

После применения миграции можно проверить через API:

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/extra-expenses/check-schema
```

В ответе должно быть:
```json
{
  "manual_expenses": {
    "has_shop_id": true,
    ...
  }
}
```

## Итоговая проверка

После всех шагов убедитесь:

1. ✅ `shop_id` колонка существует в `app.manual_expenses`
2. ✅ Индекс `ix_manual_expenses_user_shop_date` создан
3. ✅ POST /api/extra-expenses возвращает 201
4. ✅ GET /api/extra-expenses?period=30d возвращает 200
