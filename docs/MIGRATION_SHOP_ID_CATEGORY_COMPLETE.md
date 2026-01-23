# Миграция shop_id, category, updated_at для manual_expenses - ЗАВЕРШЕНО

## Выполненные изменения

### 1. Диагностика схемы

**До миграции:**
- ✅ `id`, `user_id`, `expense_date`, `amount_sum`, `comment`, `created_at`, `is_deleted` - существовали
- ❌ `shop_id` - отсутствовал
- ❌ `category` - отсутствовал
- ❌ `updated_at` - отсутствовал

**После миграции:**
- ✅ Все колонки присутствуют

### 2. Применённые миграции

#### Миграция 1: `20260123_223716_add_shop_id_to_manual_expenses`
- Добавлена колонка `shop_id uuid NULL`
- Создан индекс `ix_manual_expenses_user_shop_date` на `(user_id, shop_id, expense_date)`

#### Миграция 2: `20260124_add_category_updated_at_to_manual_expenses`
- Добавлена колонка `category text NULL`
- Добавлена колонка `updated_at timestamp with time zone NOT NULL DEFAULT now()`
- Создан индекс `ix_manual_expenses_user_date` на `(user_id, expense_date)`

### 3. Текущая схема таблицы

```sql
CREATE TABLE app.manual_expenses (
    id bigint NOT NULL DEFAULT nextval('app.manual_expenses_id_seq'::regclass),
    user_id uuid NOT NULL,
    expense_date date NOT NULL,
    amount_sum numeric NOT NULL,
    shop_id uuid NULL,
    category text NULL,
    comment text NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now(),
    is_deleted boolean NOT NULL DEFAULT false
);

-- Индексы:
CREATE INDEX ix_manual_expenses_user_shop_date ON app.manual_expenses (user_id, shop_id, expense_date);
CREATE INDEX ix_manual_expenses_user_date ON app.manual_expenses (user_id, expense_date);
```

### 4. Использование JWT dependency

В `extra_expenses.py` используется тот же подход, что и в других роутерах:
- `user_id: UUID = Depends(require_user)` - стандартный синтаксис
- `require_user` из `app.deps` обрабатывает JWT Bearer token и fallback на X-User-Id

**Примечание:** Предупреждение "JWT processing error" в логах не критично - это нормальное поведение при fallback на X-User-Id header в dev режиме.

## Проверка

### SQL проверка колонок:
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'app' AND table_name = 'manual_expenses'
ORDER BY ordinal_position;
```

**Результат:**
- ✅ Все 10 колонок присутствуют
- ✅ `shop_id` - uuid, nullable=YES
- ✅ `category` - text, nullable=YES
- ✅ `updated_at` - timestamp with time zone, nullable=NO, default=now()

### Проверка индексов:
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'app' AND tablename = 'manual_expenses';
```

**Результат:**
- ✅ `ix_manual_expenses_user_shop_date` - существует
- ✅ `ix_manual_expenses_user_date` - существует

## Следующие шаги

1. **Перезапустить API** (если запущен)
2. **Проверить POST /api/extra-expenses:**
   ```bash
   curl -X POST http://localhost:8000/api/extra-expenses \
     -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{
       "expense_date": "2026-01-24",
       "amount_sum": 1000,
       "category": "Test",
       "comment": "Test expense"
     }'
   ```
   Ожидается: `201 Created`

3. **Проверить GET /api/extra-expenses:**
   ```bash
   curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/extra-expenses?period=30d
   ```
   Ожидается: `200 OK` с списком расходов

## Файлы миграций

1. `apps/api/alembic/versions/20260123_223716_add_shop_id_to_manual_expenses.py`
2. `apps/api/alembic/versions/20260124_add_category_updated_at_to_manual_expenses.py`

## Скрипты

1. `apps/api/scripts/check_manual_expenses_schema.py` - проверка схемы
2. `apps/api/scripts/apply_shop_id_direct.py` - применение миграции shop_id (fallback)
3. `apps/api/scripts/apply_category_updated_at_migration.py` - применение миграции category/updated_at (fallback)

## Итог

✅ Все колонки добавлены
✅ Индексы созданы
✅ Миграции применены в БД `service_analytics`, схема `app`
✅ API готов к работе с полной схемой `manual_expenses`
