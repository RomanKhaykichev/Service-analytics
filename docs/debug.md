# Debug SQL Queries for VIEW and stock-current Endpoint

Этот файл содержит SQL-запросы для проверки состояния view и диагностики проблем с endpoint `/api/charts/stock-current`.

## Предварительные проверки

### 1. Проверка текущего batch для пользователя

```sql
-- Замените '<your-user-id>' на реальный UUID пользователя
SELECT * 
FROM app.v_current_batch 
WHERE user_id = '<your-user-id>';
```

**Ожидаемый результат:** Одна строка с `upload_batch_id` и `created_at` для текущего batch.

### 2. Проверка данных в fact_leftout_snapshot

```sql
-- Проверка наличия данных в fact_leftout_snapshot для текущего batch
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT barcode) as unique_barcodes,
    COUNT(marketplace_side) as non_null_marketplace_side,
    COUNT(coverage_days) as non_null_coverage_days,
    MIN(marketplace_side) as min_stock,
    MAX(marketplace_side) as max_stock,
    AVG(coverage_days) as avg_coverage_days
FROM app.fact_leftout_snapshot l
JOIN app.v_current_batch cb
  ON cb.user_id = l.user_id
 AND cb.upload_batch_id = l.upload_batch_id
WHERE l.user_id = '<your-user-id>'
  AND l.shop_id = '<your-shop-id>';
```

**Ожидаемый результат:** 
- `total_rows` > 0 (если данные загружены)
- `non_null_marketplace_side` и `non_null_coverage_days` должны быть > 0, если данные корректны

### 3. Проверка данных в fact_storage_snapshot

```sql
-- Проверка наличия данных в fact_storage_snapshot для текущего batch
SELECT 
    COUNT(*) as total_rows,
    COUNT(DISTINCT barcode) as unique_barcodes,
    COUNT(turnover_days) as non_null_turnover_days,
    COUNT(fee_total_30d) as non_null_fee_total_30d,
    AVG(turnover_days) as avg_turnover_days
FROM app.fact_storage_snapshot s
JOIN app.v_current_batch cb
  ON cb.user_id = s.user_id
 AND cb.upload_batch_id = s.upload_batch_id
WHERE s.user_id = '<your-user-id>'
  AND s.shop_id = '<your-shop-id>';
```

**Ожидаемый результат:** 
- `total_rows` > 0 (если данные загружены)
- `non_null_turnover_days` > 0, если данные корректны

## Проверка view

### 4. Проверка v_current_leftout

```sql
-- Количество строк в v_current_leftout
SELECT COUNT(*) 
FROM app.v_current_leftout 
WHERE user_id = '<your-user-id>' 
  AND shop_id = '<your-shop-id>';
```

**Ожидаемый результат:** Должно совпадать с количеством строк из проверки #2.

### 5. Проверка v_current_storage

```sql
-- Количество строк в v_current_storage
SELECT COUNT(*) 
FROM app.v_current_storage 
WHERE user_id = '<your-user-id>' 
  AND shop_id = '<your-shop-id>';
```

**Ожидаемый результат:** Должно совпадать с количеством строк из проверки #3.

### 6. Проверка v_product_current_stock (основная проверка)

```sql
-- Общая статистика по v_product_current_stock
SELECT 
    COUNT(*) as total_rows,
    COUNT(stock_qty) as non_null_stock_qty,
    COUNT(coverage_days) as non_null_coverage_days,
    COUNT(turnover_days) as non_null_turnover_days,
    COUNT(fee_total_30d) as non_null_fee_total_30d,
    MIN(stock_qty) as min_stock_qty,
    MAX(stock_qty) as max_stock_qty,
    AVG(coverage_days) as avg_coverage_days,
    AVG(turnover_days) as avg_turnover_days
FROM app.v_product_current_stock 
WHERE user_id = '<your-user-id>' 
  AND shop_id = '<your-shop-id>';
```

**Ожидаемый результат:**
- `total_rows` > 0
- `non_null_stock_qty` должно быть > 0 (если в fact_leftout_snapshot есть marketplace_side)
- `non_null_coverage_days` должно быть > 0 (если в fact_leftout_snapshot есть coverage_days)
- `non_null_turnover_days` должно быть > 0 (если в fact_storage_snapshot есть turnover_days)

### 7. Просмотр примеров данных из v_product_current_stock

```sql
-- Первые 20 строк с данными
SELECT 
    barcode,
    sku,
    product_name,
    stock_qty,
    coverage_days,
    turnover_days,
    fee_total_30d
FROM app.v_product_current_stock 
WHERE user_id = '<your-user-id>' 
  AND shop_id = '<your-shop-id>'
ORDER BY stock_qty DESC NULLS LAST
LIMIT 20;
```

**Ожидаемый результат:** Строки с заполненными `stock_qty`, `coverage_days`, `turnover_days` (если данные есть в исходных таблицах).

### 8. Проверка типов колонок view

```sql
-- Проверка типов данных колонок в v_product_current_stock
SELECT 
    column_name, 
    data_type, 
    numeric_precision, 
    numeric_scale,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'app' 
  AND table_name = 'v_product_current_stock'
ORDER BY ordinal_position;
```

**Ожидаемый результат:**
- `stock_qty`: `integer`
- `coverage_days`: `numeric(10,2)`
- `turnover_days`: `numeric(18,4)`
- `fee_total_30d`: `numeric(18,2)`

## Диагностика проблем

### Проблема: stock_qty/coverage_days/turnover_days возвращают NULL

**Проверка 1:** Убедитесь, что данные есть в исходных таблицах:

```sql
-- Проверка marketplace_side в fact_leftout_snapshot
SELECT 
    barcode,
    marketplace_side,
    coverage_days,
    CASE 
        WHEN marketplace_side IS NULL THEN 'NULL'
        WHEN marketplace_side::text ~ '^[0-9]+$' THEN 'VALID_INT'
        ELSE 'INVALID: ' || marketplace_side::text
    END as marketplace_side_status
FROM app.fact_leftout_snapshot l
JOIN app.v_current_batch cb
  ON cb.user_id = l.user_id
 AND cb.upload_batch_id = l.upload_batch_id
WHERE l.user_id = '<your-user-id>'
  AND l.shop_id = '<your-shop-id>'
  AND l.barcode IS NOT NULL
LIMIT 10;
```

**Проверка 2:** Проверка join по barcode (возможна проблема с пробелами):

```sql
-- Проверка различий в barcode между leftout и storage
SELECT 
    l.barcode as leftout_barcode,
    s.barcode as storage_barcode,
    length(l.barcode) as leftout_len,
    length(s.barcode) as storage_len,
    l.barcode = s.barcode as exact_match,
    trim(l.barcode) = trim(s.barcode) as trim_match
FROM app.v_current_leftout l
LEFT JOIN app.v_current_storage s
  ON s.user_id = l.user_id
 AND s.shop_id = l.shop_id
 AND trim(s.barcode) = trim(l.barcode)
WHERE l.user_id = '<your-user-id>'
  AND l.shop_id = '<your-shop-id>'
  AND l.barcode IS NOT NULL
LIMIT 10;
```

### Проблема: Ошибка 42P16 при применении миграции

**Решение:** Убедитесь, что миграция `0040_recreate_views.sql` использует `DROP VIEW` перед `CREATE VIEW`, а не `CREATE OR REPLACE VIEW`.

Проверьте, что миграция применена:

```sql
-- Проверка существования view
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'app'
  AND table_name IN (
    'v_current_batch',
    'v_current_leftout',
    'v_current_storage',
    'v_product_current_stock'
  )
ORDER BY table_name;
```

## Проверка после применения миграции

После применения миграции `db/0040_recreate_views.sql` выполните все проверки выше, чтобы убедиться, что:

1. ✅ View созданы без ошибок
2. ✅ Типы колонок соответствуют ожидаемым
3. ✅ Данные возвращаются корректно (не NULL, когда должны быть значения)
4. ✅ Join по barcode работает корректно (с trim)

## Быстрая проверка для endpoint

```sql
-- Имитация запроса endpoint /api/charts/stock-current
SELECT
  barcode::text AS barcode,
  sku::text AS sku,
  product_name::text AS product_name,
  stock_qty,
  coverage_days,
  turnover_days
FROM app.v_product_current_stock
WHERE user_id = '<your-user-id>'
  AND (shop_id = COALESCE(CAST('<your-shop-id>' AS uuid), shop_id))
ORDER BY stock_qty DESC NULLS LAST
LIMIT 200;
```

Этот запрос должен возвращать те же данные, что и endpoint `/api/charts/stock-current`.
