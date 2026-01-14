# Database Migration Scripts

## Порядок выполнения миграций

### Инициализация БД (первый запуск)

1. **001_schema.sql** - Создание схемы и всех таблиц (выполнить первым)
2. **002_load_facts.sql** - SQL процедуры для загрузки данных (опционально, если используете ручную загрузку)
3. **003_switch_to_barcode.sql** - Миграция на barcode-based mapping (выполнить после 001)
4. **004_views.sql** - Создание аналитических представлений
5. **005_populate_facts.sql** - **ОБЯЗАТЕЛЬНО**: SQL функция для автоматической загрузки fact таблиц из staging (нужна для import_batch.py)

### Миграции для существующих БД

Миграции из папки `db/migrations/` применяются к уже существующим базам данных для обновления структуры.

**Текущие миграции:**
- **005_fix_product_current_stock_view.sql** - Исправляет view `v_product_current_stock`: убирает regex, использует прямые CAST для стабильных типов колонок

## Применение миграций

### Автоматическое применение (рекомендуется)

Используйте скрипт `db/apply_migrations.py`:

```bash
# Установите зависимости (если еще не установлены)
pip install psycopg python-dotenv

# Применить все миграции
python db/apply_migrations.py

# Проверить, что будет сделано (dry-run)
python db/apply_migrations.py --dry-run

# Применить конкретную миграцию
python db/apply_migrations.py --migration-file 005_fix_product_current_stock_view.sql
```

Скрипт автоматически:
- Подключается к БД используя переменные окружения из `.env`
- Проверяет, какие миграции уже применены
- Применяет миграции в правильном порядке
- Показывает результат

### Ручное применение

Если нужно применить миграцию вручную:

```bash
# В PowerShell или через psql:
psql -h localhost -U <user> -d <database> -f db/migrations/005_fix_product_current_stock_view.sql
```

Или выполните содержимое файла в pgAdmin / DBeaver.

## Важно

- Файл `005_populate_facts.sql` **обязательно** должен быть выполнен в БД перед использованием `import/import_batch.py`
- Без этой функции импорт будет падать с ошибкой "функция app.populate_facts не существует"
- Миграции используют `DROP VIEW` перед `CREATE VIEW` для избежания ошибки PostgreSQL 42P16 при изменении типов колонок

## Проверка после применения миграции

После применения миграции `005_fix_product_current_stock_view.sql` выполните проверочный запрос:

```sql
SELECT 
  count(*) as total_rows,
  count(stock_qty) as non_null_stock_qty,
  count(coverage_days) as non_null_coverage_days,
  count(turnover_days) as non_null_turnover_days
FROM app.v_product_current_stock 
WHERE user_id = '<your-user-uuid>';
```

**Ожидаемый результат:**
- `total_rows` > 0 (если данные загружены)
- `non_null_stock_qty` и `non_null_coverage_days` должны быть > 0, если данные есть в `app.fact_leftout_snapshot`
- `non_null_turnover_days` должен быть > 0, если данные есть в `app.fact_storage_snapshot`

Подробные SQL-запросы для диагностики см. в `docs/debug.md`.
