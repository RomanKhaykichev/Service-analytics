# Стандарт нормализации штрихкода

## Общие принципы

### Canonical barcode
- **Canonical barcode** = `fact_*.barcode` (raw из Excel, но с применением `TRIM`)
- Это исходные данные из файла, очищенные только от пробелов по краям
- Хранится в таблицах `fact_sales`, `fact_leftout_snapshot`, `fact_storage_snapshot` в колонке `barcode`

### Нормализованный штрихкод (barcode_norm)
- **barcode_norm** вычисляется ТОЛЬКО как SQL expression или хранится в `map_shop_barcode.barcode_norm`
- **ЗАПРЕЩЕНО** добавлять физические колонки `barcode_norm` или `barcode_key` в таблицы:
  - `stg_*` (staging tables)
  - `fact_*` (fact tables)

### Разрешенные места использования barcode_norm

1. **SQL CTE/join/view** - вычисляемое выражение внутри запроса
2. **map_shop_barcode.barcode_norm** - единственная таблица, где `barcode_norm` хранится как физическая колонка
3. **Python helper** - функция для формирования SQL expression (НЕ хранить в БД)

## Canonical expression

Стандартная формула нормализации штрихкода:

```sql
NULLIF(TRIM(regexp_replace(CAST(x AS text), '\s+', '', 'g')), '')
```

Где `x` - колонка или выражение со штрихкодом.

### Что делает эта формула:
- `CAST(x AS text)` - приводит значение к тексту (для numeric штрихкодов)
- `regexp_replace(..., '\s+', '', 'g')` - удаляет все пробелы внутри строки
- `TRIM(...)` - обрезает пробелы по краям
- `NULLIF(..., '')` - возвращает NULL, если результат пустой

### Примеры:
- `' 123 45 '` → `'12345'`
- `'   '` → `NULL`
- `12345` (numeric) → `'12345'`
- `'00123'` → `'00123'` (лидирующие нули сохраняются)

## Использование в коде

### Python helper

Используйте функцию `barcode_norm_sql(col)` из `app.utils.barcode`:

```python
from app.utils.barcode import barcode_norm_sql

# В SQL запросе
db.execute(text(f"""
    SELECT {barcode_norm_sql('fs.barcode')} AS barcode_norm
    FROM fact_sales fs
"""))
```

### JOIN по штрихкоду

При связывании таблиц используйте нормализацию напрямую в JOIN:

```sql
LEFT JOIN map_shop_barcode m
    ON m.user_id = s.user_id
   AND m.barcode_norm = NULLIF(TRIM(regexp_replace(CAST(s.barcode AS text), '\s+', '', 'g')), '')
```

Или через helper:

```python
from app.utils.barcode import barcode_norm_sql

db.execute(text(f"""
    SELECT ...
    FROM fact_sales s
    LEFT JOIN map_shop_barcode m
        ON m.user_id = s.user_id
       AND m.barcode_norm = {barcode_norm_sql('s.barcode')}
"""))
```

## Запрещенные практики

❌ **НЕ ДОБАВЛЯЙТЕ** физические колонки:
- `stg_sales.barcode_norm`
- `stg_leftout.barcode_norm`
- `stg_storage.barcode_norm`
- `fact_sales.barcode_norm`
- `fact_leftout_snapshot.barcode_norm`
- `fact_storage_snapshot.barcode_norm`

❌ **НЕ ИСПОЛЬЗУЙТЕ** `barcode_key` как физическую колонку

✅ **ИСПОЛЬЗУЙТЕ** только:
- Вычисляемые выражения в CTE
- `map_shop_barcode.barcode_norm` (единственное место хранения)
- Helper функцию для генерации SQL expression

## Миграции

Если в старых миграциях есть добавление `barcode_norm` в `stg_*` или `fact_*` таблицы - это устаревшие миграции. Новые миграции не должны добавлять такие колонки.

Единственная таблица с `barcode_norm` как физической колонкой:
- `app.map_shop_barcode.barcode_norm` (создана миграцией `20260126_create_map_shop_barcode`)
