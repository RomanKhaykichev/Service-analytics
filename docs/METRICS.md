# Метрики KPI - Документация

## Обзор

Данный документ описывает все метрики, рассчитываемые в эндпоинте `/api/kpi/summary`, их источники данных и формулы расчёта.

## Блок "Продажи"

### 1. Заказы
- **Количество (ordersCount)**: `SUM(qty)` из `fact_sales` (без фильтра по статусу)
- **Выручка (ordersValue)**: `SUM(revenue_sum)` из `fact_sales` (без фильтра по статусу)
- **Источник**: `sells_report` → `fact_sales`
- **Фильтры**: `period`, `shop_id`, `user_id`

### 2. В обработке
- **Количество (processingCount)**: `SUM(qty)` где `lower(trim(status)) = 'в обработке'`
- **Выручка (processingValue)**: `SUM(revenue_sum)` где `lower(trim(status)) = 'в обработке'`
- **Источник**: `sells_report` → `fact_sales`
- **Фильтры**: `period`, `shop_id`, `user_id`

### 3. Выкупы (Завершен)
- **Количество (completedCount)**: `SUM(qty)` где `lower(trim(status)) IN ('завершен', 'завершён')`
- **Выручка (completedValue)**: `SUM(revenue_sum)` где `lower(trim(status)) IN ('завершен', 'завершён')`
- **Источник**: `sells_report` → `fact_sales`
- **Фильтры**: `period`, `shop_id`, `user_id`

### 4. Возвраты
- **Количество (returnsCount)**: файл sells_report из колонки Количество со статусом из колонки Статус «отменен» — `SUM(qty)` где `lower(trim(status)) IN ('отменен', 'отменён')`
- **Денежно (returnsValue, после / в блоке Продажи)**: файл sells_report (из колонки Количество × из колонки Цена (сумы)) со статусом «отменен» — `SUM(qty * price_sum)` где `lower(trim(status)) IN ('отменен', 'отменён')`
- **Источник**: `sells_report` → `fact_sales`
- **Фильтры**: `period`, `shop_id`, `user_id`

### 5. Процент возврата (returnRate)
- **Формула**: `(SUM(qty) по отменен / SUM(qty) всего) * 100`
- **Источник**: `fact_sales`
- **Безопасное деление**: Если `SUM(qty) = 0`, возвращается `0`

### 6. Средний чек (averageCheck)
- **Формула**: `SUM(revenue_sum) / SUM(qty)` где `lower(trim(status)) IN ('завершен', 'завершён')`
- **Источник**: `fact_sales`
- **Округление**: До целых сум (без копеек)
- **Безопасное деление**: Если `SUM(qty) = 0`, возвращается `0`

## Блок "Финансы"

### 1. Выручка (revenue)
- **Формула**: `SUM(revenue_sum)` где `lower(trim(status)) IN ('завершен', 'завершён')`
- **Источник**: `sells_report` → `fact_sales`
- **Фильтры**: `period`, `shop_id`, `user_id`
- **Примечание**: Совпадает с `completedValue`

### 2. Расходы (totalExpenses)
- **Формула**: `uzum_commission + uzum_logistics + uzum_ads + uzum_storage + uzum_fines + product_cost_total`
- **Компоненты**:
  - Комиссия UZUM (`uzum_commission`)
  - Логистика UZUM (`uzum_logistics`)
  - Реклама UZUM (`uzum_ads`)
  - Хранение UZUM (`uzum_storage`)
  - Штрафы UZUM (`uzum_fines`)
  - Себестоимость проданных товаров (`product_cost_total`)
- **Источники**: `fact_sales`, `fact_expenses`

### 3. Прибыль (profit)
- **Формула**: `revenue - total_expenses`
- **Источник**: Расчётный (на основе выручки и расходов)

### 4. Рентабельность продаж (salesProfitability)
- **Формула**: `(revenue / product_cost_completed) * 100`
- **Источник**: `fact_sales` (только завершённые заказы)
- **Примечание**: `product_cost_completed` = `SUM(cogs_sum)` где `lower(trim(status)) IN ('завершен', 'завершён')`
- **Важно**: В `fact_sales` поле `cogs_sum` уже является итоговой себестоимостью по строке (не единичной)
- **Безопасное деление**: Если `product_cost_completed = 0`, возвращается `0`

### 5. ROI (roi)
- **Формула**: `((revenue - product_cost_completed) / product_cost_completed) * 100`
- **Источник**: `fact_sales` (только завершённые заказы)
- **Безопасное деление**: Если `product_cost_completed = 0`, возвращается `0`

### 6. Тренд выручки (revenueTrend)
- **Legacy (revenueTrend)**: Процентное изменение выручки относительно предыдущего периода
  - **Формула**: `((current_revenue - previous_revenue) / previous_revenue) * 100`
- **Детальный объект (revenueTrendDetail)**:
  - `current_revenue`: Выручка текущего периода
  - `previous_revenue`: Выручка аналогичного периода ранее
  - `delta_abs`: Абсолютное изменение (`current_revenue - previous_revenue`)
  - `delta_pct`: Процентное изменение (в процентах)
- **Источник**: `fact_sales`
- **Примечание**: "Аналогичный период ранее" = такой же по длине интервал непосредственно перед текущим периодом

### 7. Упущенная выручка (lostRevenue)
- **Формула**: `SUM((avg_daily_sales * 15) * price)` для товаров где `stock_qty = 0` и `avg_daily_sales > 0`
- **Условия**:
  - `stock_qty = 0` (нет остатков)
  - `avg_daily_sales > 0` (были продажи в периоде)
  - Цена определяется из периода или fallback из окна 90 дней
- **Источники**: `fact_leftout_snapshot` (остатки), `fact_sales` (продажи и цены)
- **Примечание**: Используется `marketplace_side` из `fact_leftout_snapshot` как единый источник склада

## Блок "Расходы"

### 1. Комиссия UZUM (uzumCommission)
- **Формула**: `SUM(commission_sum)` где `lower(trim(status)) IN ('завершен', 'завершён')`
- **Источник**: `sells_report` → `fact_sales`
- **Фильтры**: `period`, `shop_id`, `user_id`
- **ТЗ**: файл sells_report из колонки Комиссия маркетплейса (сумы) со статусом из колонки Статус «Завершен»

### 2. Логистика UZUM (uzumLogistics)
- **Формула**: `SUM(logistics_sum)` где `lower(trim(status)) IN ('завершен', 'завершён')`
- **Источник**: `sells_report` → `fact_sales`
- **Фильтры**: `period`, `shop_id`, `user_id`
- **ТЗ**: файл sells_report из колонки Логистический сбор со статусом из колонки Статус «Завершен»

### 3. Реклама UZUM (uzumAds)
- **Формула**: `SUM(cost_sum)` где `source ILIKE '%маркетинг%' OR source ILIKE '%marketing%'` И `operation_type ILIKE '%оплат%' OR operation_type ILIKE '%payment%'`
- **Источник**: `expenses-report` → `fact_expenses`
- **Фильтры**: `period` (по `date_written_off`), `user_id`
- **ТЗ**: `sum(Стоимость (сумы))` где `Источник="Маркетинг"` AND `Тип операции="Оплата"`

### 4. Хранение UZUM (uzumStorage)
- **Формула**: `SUM(cost_sum)` где `source = 'Склад'` и `operation_type = 'Оплата'` минус `SUM(cost_sum)` где `source = 'Склад'` и `operation_type = 'Возврат'`
- **Источник**: `expenses-report` → `fact_expenses`
- **Фильтры**: `period` (по `date_written_off`), `user_id`
- **ТЗ**: сумма по колонке «Стоимость (сумы)» при Источник = «Склад» и Тип операции = «Оплата» минус сумма при Источник = «Склад» и Тип операции = «Возврат»

### 5. Штрафы UZUM (uzumFines)
- **Формула**: `SUM(amount_sum)` где `service ILIKE '%штраф%'`
- **Источник**: `expenses-report` → `fact_expenses`
- **Фильтры**: `period` (по `date_written_off`), `user_id`
- **ТЗ**: `sum(Сумма (сумы))` где `Услуга ILIKE '%Штраф%'`

### 6. Себестоимость проданных товаров (productCost)
- **productCostTotal** и **productCostCompleted**: `SUM(cogs_sum * qty)` где `lower(trim(status)) IN ('завершен', 'завершён')`
- **Источник**: `sells_report` → `fact_sales`
- **Фильтры**: `period`, `shop_id`, `user_id`
- **ТЗ**: файл sells_report (из колонки Себестоимость (сумы) * из колонки Количество) со статусом из колонки Статус «Завершен»

## Блок "Склад"

### 1. Товар на складе (stockQuantity)
- **Формула**: `SUM(marketplace_side)` из `fact_leftout_snapshot`
- **Источник**: `left-out-report` → `fact_leftout_snapshot`
- **ТЗ**: `sum(На стороне маркетплейса (всего в продаже, в пути, на складах и фотостудии), шт)`
- **Фильтры**: `shop_id`, `user_id` (не зависит от `period`)
- **Примечание**: Используется самый свежий snapshot (`MAX(loaded_at)`)

### 2. Себестоимость товара на складе (stockCost)
- **Формула**: `SUM(stock_qty * unit_cogs)` по каждому товару (SKU/barcode)
- **Где**:
  - `stock_qty` = `COALESCE(marketplace_side, 0)` из `fact_leftout_snapshot` (left-out-report)
  - `unit_cogs` = единичная себестоимость из `fact_sales` (sells-report)
- **Расчет unit_cogs**:
  - В `fact_sales` поле `cogs_sum` хранится как **итоговая себестоимость по строке (total)**, а не единичная себестоимость
  - Это подтверждается кодом импорта (`import_batch.py`, `apps/api/app/routes/imports.py`): `cogs_sum` берется напрямую из `cogs_raw` без умножения на `qty`
  - Поэтому: `unit_cogs = SUM(cogs_sum) / NULLIF(SUM(qty), 0)` по завершённым заказам
  - Статус учитывается как `lower(trim(status)) IN ('завершен', 'завершён')`
- **Сопоставление товаров**:
  - Связь `fact_leftout_snapshot` и `fact_sales` по SKU и/или barcode
  - Приоритет: сначала по SKU, затем по barcode (если не найдено по SKU)
- **Окно для unit_cogs**:
  - **Фиксированное окно**: всегда последние 90 дней от `data_end_date` (максимальная дата в данных пользователя)
  - **НЕ зависит от параметра `period`** запроса пользователя
  - Это обеспечивает стабильность метрики `stock_cost` независимо от выбранного периода фильтра
  - Причина: себестоимость товара на складе должна быть консистентной метрикой, не меняющейся при смене периода анализа
- **Фильтры**: `period`, `shop_id`, `user_id` (применяются к расчету unit_cogs из fact_sales)
- **Источники**: 
  - `stock_qty`: `left-out-report` → `fact_leftout_snapshot`
  - `unit_cogs`: `sells_report` → `fact_sales`

### Фильтрация склада по магазинам
- **Источник фильтра**: `left-out-report` → `fact_leftout_snapshot` → поле `shop_id`
- **ТЗ**: В фильтре магазинов для данных склада источник — файл left-out (left-out-report) колонка "Магазин"
- **Реализация**: 
  - `fact_leftout_snapshot.shop_id` заполняется из `dim_shop` по `shop_name` из left-out-report при импорте
  - Фильтрация склада использует `shop_id` (UUID) из параметра запроса: `(:shop_id IS NULL OR shop_id = CAST(:shop_id AS uuid))`
  - `/api/shops` возвращает объединенный список магазинов из `dim_shop` (left-out-report) и `fact_sales` (sells-report) для совместимости

### 3. Розничная цена товара на складе (stockRetailPrice)
- **Формула**: `SUM(potential_total)` из `fact_leftout_snapshot` (если есть), иначе `SUM(stock_qty * avg_price)`
- **Источники**: 
  - Основной: `fact_leftout_snapshot` (`potential_total`)
  - Fallback: `fact_sales` (`revenue_sum / qty` для завершённых заказов)
- **ТЗ**: `sum(Потенциальная сумма к получению за все остатки, сум)`
- **Фильтры**: `shop_id`, `user_id` (не зависит от `period`)

### 4. Дополнительные метрики склада
- **stockSkuTotal**: Общее количество SKU в snapshot
- **stockSkuWithStock**: Количество SKU с ненулевыми остатками
- **stockSnapshotAt**: Дата и время последнего snapshot
- **stockIsZero**: Флаг, указывающий что остатков нет
- **stockZeroReason**: Причина отсутствия остатков (`no_snapshot_data` или `all_zero_in_snapshot`)

## Нормализация статусов

Все статусы нормализуются через `lower(trim(status))`:

- **В обработке**: `'в обработке'`
- **Завершен**: `'завершен'` или `'завершён'` (поддержка обоих вариантов)
- **Отменен**: `'отменен'` или `'отменён'` (поддержка обоих вариантов)

## Фильтры

### Период (period)
- **7d**: Последние 7 дней
- **30d**: Последние 30 дней
- **90d**: Последние 90 дней
- **all**: Все данные (без фильтра по датам)

### Магазин (shop_id)
- **NULL**: Все магазины
- **UUID**: Конкретный магазин

### Пользователь (user_id)
- Обязательный параметр (из JWT или заголовка `X-User-Id`)

## Безопасность расчётов

Все расчёты используют безопасное деление через `NULLIF` или проверки на ноль:
- `COALESCE(SUM(...), 0)` для сумм
- `NULLIF(SUM(...), 0)` для делителей
- Проверки `if denominator > 0` в Python коде

## Источники данных

### Таблицы фактов
- `app.fact_sales` - Продажи (из `sells_report`)
- `app.fact_expenses` - Расходы (из `expenses-report`)
- `app.fact_leftout_snapshot` - Остатки (из `left-out-report`)
- `app.fact_storage_snapshot` - Хранение (из `storage-report`, используется только для fee_total_30d)

### Таблицы измерений
- `app.dim_shop` - Магазины
- `app.map_shop_sku` - Маппинг магазинов и SKU

## API Эндпоинт

### GET /api/kpi/summary

**Параметры**:
- `period` (query, optional): Период (`7d`, `30d`, `90d`, `all`), по умолчанию `30d`
- `shop_id` (query, optional): UUID магазина или `null` для всех магазинов

**Ответ**: JSON объект со всеми метриками (см. схему `KPISummaryResponse`)

**Пример**:
```json
{
  "revenue": 1000000.0,
  "totalExpenses": 500000.0,
  "profit": 500000.0,
  "salesProfitability": 200.0,
  "roi": 100.0,
  "revenueTrend": 10.5,
  "revenueTrendDetail": {
    "current_revenue": 1000000.0,
    "previous_revenue": 900000.0,
    "delta_abs": 100000.0,
    "delta_pct": 11.11
  },
  "uzumCommission": 100000.0,
  "uzumLogistics": 50000.0,
  "uzumAds": 20000.0,
  "uzumStorage": 10000.0,
  "uzumFines": 5000.0,
  "productCost": 315000.0,
  "stockQuantity": 1000.0,
  "stockCost": 200000.0,
  "stockRetailPrice": 500000.0
}
```

## Изменения и версионирование

### Версия 1.0 (текущая)
- Реализованы все метрики согласно ТЗ
- Добавлена поддержка обоих вариантов написания статусов (с ё и без)
- Добавлен расчёт Хранения UZUM
- Улучшен расчёт тренда выручки (добавлен детальный объект)
- Исправлен расчёт себестоимости остатков (оценочная на основе avg_cogs)
