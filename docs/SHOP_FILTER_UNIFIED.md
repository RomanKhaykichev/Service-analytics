# Единый контракт фильтрации по магазинам (seller-storage, barcode_norm)

## Инварианты (не нарушать)

1. **Источник списка магазинов** — только seller-storage: backend-таблица `app.fact_storage_snapshot.shop_raw` (колонка «Магазин»), не SKU и не dim_shop.
2. **Привязка продаж/leftout/услуг к магазину** — только через штрихкод: `barcode_norm` (fallback: `COALESCE(barcode_norm, normalize(barcode))`).
3. **SQL не зависит от current_schema=public**: везде используется `qname()` (схема `app`) и в `get_db()` выполняется `SET search_path TO app, public`.

## Изменённые файлы

### Backend (apps/api)

| Файл | Изменения |
|------|-----------|
| `app/utils/shop_filter.py` | **Новый.** `normalize_shop()`, `storage_barcode_filter_sql()`, `shop_filter_condition()` — единый helper для фильтра по магазину. |
| `app/db.py` | Уже: `SET search_path TO app, public` в `get_db()`; `qname()`. |
| `app/routes/kpi.py` | Использует `normalize_shop`, `shop_filter_condition`, `storage_barcode_filter_sql`; удалён дублирующий `re`. |
| `app/routes/charts.py` | Во всех daily/sales эндпоинтах: `normalize_shop`, `shop_filter_condition`; добавлен параметр `shop` и фильтр в revenue-daily, uzum-services-daily, orders-sales-daily, stock-current. |
| `app/routes/debug.py` | Добавлен `GET /api/debug/shop-filter?shop=...` — диагностика: shop, shop_norm, barcode_count в наборе магазина. |
| `app/schemas/charts.py` | В фильтрах ответов добавлено поле `shop: Optional[str]` (RevenueFilters, UzumServicesFilters, OrdersSalesDailyFilters, StockFilters). |
| `tests/test_shop_filter.py` | **Новый.** Unit-тесты для normalize_shop, storage_barcode_filter_sql, shop_filter_condition. |

### Frontend (apps/web)

| Файл | Изменения |
|------|-----------|
| `src/pages/Index.tsx` | Единый источник правды: `store` → `selectedShop`; передаётся `shop: selectedShop` в useDashboardMetrics, useRevenueDaily, useUzumServicesDaily, useStockCurrent; в DailyView передаётся `shop: selectedShop`. |
| `src/hooks/useDashboardMetrics.ts` | Уже: `shop` в queryKey и в запросе к `/api/kpi/summary`. |
| `src/hooks/useRevenueDaily.ts` | Уже: `shop` в queryKey и в запросе. |
| `src/hooks/useUzumServicesDaily.ts` | Уже: `shop` в queryKey и в запросе. |
| `src/hooks/useOrdersSalesDaily.ts` | Уже: `shop` в queryKey и в запросе. |
| `src/hooks/useStockCurrent.ts` | Добавлен `shop` в параметры, queryKey (через deps), и в запрос к `/api/charts/stock-current`. |
| `src/components/dashboard/DailyView.tsx` | Уже: принимает `shop`, передаёт в useOrdersSalesDaily. |

## Endpoints с включённым shop-фильтром

| Endpoint | Query param | Поведение |
|----------|-------------|-----------|
| `GET /api/kpi/summary` | `shop` (string) | KPI-метрики только по товарам из fact_storage_snapshot выбранного магазина (barcode_norm). |
| `GET /api/charts/revenue-daily` | `shop` | Продажи по дням — только по barcode set магазина. |
| `GET /api/charts/uzum-services-daily` | `shop` | Commission/logistics из fact_sales по barcode set; storage/ads/fines из fact_expenses без фильтра по магазину. |
| `GET /api/charts/orders-sales-daily` | `shop` | График заказов и продаж по дням — только по barcode set магазина. |
| `GET /api/charts/stock-current` | `shop` | Текущие остатки — только товары из barcode set магазина (view v_product_current_stock с alias v). |
| `GET /api/debug/shop-filter` | `shop` | Диагностика: shop_norm и barcode_count в наборе магазина. |

## Проверка

1. **Запуск**: API — `cd apps/api && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`; фронт — `cd apps/web && npm run dev`.
2. **Источник магазинов**: в фильтре на Сводке/По дням список магазинов должен браться только из seller-storage (эндпоинт списка магазинов для storage уже используется в SummaryFilters).
3. **Выбор магазина**: выбрать магазин из выпадающего списка (3 штуки из storage) → все виджеты на вкладках «Сводка» и «По дням» должны пересчитаться (KPI, Продажи по дням, Услуги UZUM, График заказов и продаж, остатки по товарам).
4. **Снять фильтр**: «Все магазины» → данные снова общие.
5. **Network**: в запросах к перечисленным endpoints при выбранном магазине должен быть query-параметр `shop=...`.
6. **Диагностика**: `GET /api/debug/shop-filter?shop=НАЗВАНИЕ%20МАГАЗИНА` с заголовком `X-User-Id` возвращает `shop_norm` и `barcode_count_in_shop_set`.
7. **Тесты**: `cd apps/api && python -m pytest tests/test_shop_filter.py -v` (при установленном pytest).

## Почему магазины только из storage и как привязка по штрихкоду

- **Магазины только из seller-storage**: в ТЗ фильтр магазина на Сводке/По дням привязан к «колонке Магазин» из отчёта seller-storage. В БД это `app.fact_storage_snapshot.shop_raw`. Другие источники (dim_shop, SKU) не используются для этого фильтра, чтобы не смешивать разные справочники.
- **Привязка по barcode_norm**: продажи и остатки привязаны к строкам storage по штрихкоду. Для выбранного магазина берётся множество `(user_id, barcode_norm)` из `fact_storage_snapshot` с `shop_raw` = выбранный магазин (нормализованный). Все запросы к fact_sales / fact_leftout_snapshot / view остатков ограничиваются этим множеством через `EXISTS (SELECT 1 FROM app.fact_storage_snapshot fss WHERE ... AND barcode match AND shop_norm = :shop_norm)`. Так агрегации остаются согласованными и не ломаются.

## Acceptance criteria (кратко)

- При выборе магазина все виджеты на «Сводка» и «По дням» меняются согласованно.
- Нет 500 из-за схемы (public/app) или отсутствующих колонок (barcode_norm есть или fallback в SQL).
- Магазины в фильтре строго из seller-storage (без мусора).
- Связка по штрихкоду работает и не ломает агрегации.
