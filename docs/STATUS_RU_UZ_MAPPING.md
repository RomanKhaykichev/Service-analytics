# Сопоставление статусов RU ↔ UZ (выгрузки продаж)

Проверка выполнена по файлам:
- **RU:** `Выгрузки_ RU/sells_report_4_shops_...xlsx` (колонка «Статус»)
- **UZ:** `Выгрузки_Uzb/sells_report_4_shops_...xlsx` (колонка «Holati»)

## Уникальные значения в выгрузках

| RU (Статус) | UZ (Holati) | Кол-во строк | Назначение |
|-------------|-------------|--------------|------------|
| Завершен    | Yakunlandi  | 789          | Выкупы (completed) |
| В обработке | Qayta ishlanmoqda | 181 | В обработке (processing) |
| Отменен     | Bekor qilindi | 467        | Отменённые (cancelled) |

Количество строк по каждому статусу совпадает в RU и UZ выгрузках → сопоставление корректно.

## Используемое в коде сопоставление

| Русский       | Узбекский (в коде)                    | Где учтено |
|---------------|----------------------------------------|------------|
| Завершен      | Yetkazilgan, Yakunlangan, **Yakunlandi** | value_mappings, metrics.py, statuses.py |
| В обработке   | Qayta ishlashda, Qayta ishlanmoqda, Jarayonda | везде |
| Отменен       | Bekor qilindi, Rad etildi              | везде |

**Уточнение:** в реальной выгрузке UZUM для «Завершен» используется именно **Yakunlandi** (не Yakunlangan). Вариант `Yakunlandi` добавлен в маппинг и в SQL-условия (completed / выкупы, выручка).

## Файлы кода

- `apps/api/app/utils/value_mappings.py` — при импорте переводит статусы UZ → RU в staging.
- `apps/api/app/utils/metrics.py` — условия для KPI и графиков (completed, revenue, processing, cancelled).
- `apps/api/app/utils/statuses.py` — условия для графиков и фильтров (get_status_sql_condition, is_completed и т.д.).

После правок выкупы и выручка по узбекской выгрузке считаются по тем же правилам, что и по русской.
