# Диагностика связей по штрихкоду

## Используемые таблицы и колонки

### 1. fact_leftout_snapshot (left-out-report)
- **barcode** (text) - колонка "Штрихкод" из файла
- **in_sale** (int) - колонка "В продаже, шт" из файла
- **shop_id** (uuid) - магазин
- **loaded_at** (timestamptz) - дата загрузки snapshot

### 2. fact_storage_snapshot (seller-storage)
- **barcode** (text) - колонка "Штрихкод" из файла
- **avg_stock_15d** (numeric) - средний остаток за 15 дней
- **avg_sales_15d** (numeric) - средние продажи за 15 дней
- **fbo_stock_total** (int) - всего на складе FBO
- **fee_total_30d** (numeric) - стоимость хранения за 30 дней
- **shop_id** (uuid) - магазин
- **loaded_at** (timestamptz) - дата загрузки snapshot

### 3. fact_sales (sells_report)
- **barcode** (text) - колонка "Штрихкод" из файла
- **qty** (int) - количество проданных единиц
- **revenue_sum** (numeric) - выручка (сумы)
- **cogs_sum** (numeric) - себестоимость (сумы)
- **price_sum** (numeric) - цена (сумы)
- **shop_id** (uuid) - магазин (может быть NULL)
- **date_created** (timestamptz) - дата создания заказа

## Нормализация штрихкода

Для связывания используется нормализованный штрихкод:
```sql
NULLIF(TRIM(regexp_replace(barcode, '\s+', '', 'g')), '')
```

Это:
- Удаляет все пробелы внутри строки
- Обрезает пробелы по краям
- Сохраняет лидирующие нули (не кастится в numeric)
- Возвращает NULL если результат пустой

## Использование скрипта

```bash
# Для конкретного пользователя
python apps/api/scripts/check_barcode_links.py <user_id>

# Для конкретного пользователя и магазина
python apps/api/scripts/check_barcode_links.py <user_id> <shop_id>
```

## Что проверяет скрипт

1. **Заполненность штрихкода** - сколько строк с пустым barcode в каждой таблице
2. **Coverage leftout -> sales** - процент barcode из leftout, которые есть в sales за последние 90 дней
3. **Coverage storage -> sales** - процент barcode из storage, которые есть в sales за последние 90 дней
4. **Coverage leftout <-> storage** - пересечение barcode между leftout и storage
5. **Примеры несоответствий** - топ-20 barcode, которые есть в одном источнике, но нет в другом
6. **Анализ форматов** - проверка пробелов, лидирующих нулей, длины

## Интерпретация результатов

- **≥ 80% совпадений** - ✅ Нормальная связь
- **50-80% совпадений** - ⚠️ Частичная связь (возможны проблемы с форматами)
- **< 50% совпадений** - ❌ Проблема (требуется проверка данных)
