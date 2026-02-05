#!/usr/bin/env python3
"""
Очистить записи в таблице Доп. расходы (app.manual_expenses).
Оставить только данные за: 24.11.2025, 17.11.2025, 10.11.2025, 03.11.2025.

Запуск из корня репозитория:
  python apps/api/scripts/clean_extra_expenses_keep_dates.py
или из apps/api:
  python scripts/clean_extra_expenses_keep_dates.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.settings import get_settings
from app.db import engine
from sqlalchemy import text

settings = get_settings()
SCHEMA = settings.DB_SCHEMA
TABLE = "manual_expenses"

# Даты, которые оставляем (остальные удаляем)
KEEP_DATES = ["2025-11-24", "2025-11-17", "2025-11-10", "2025-11-03"]


def main():
    qname_table = f'"{SCHEMA}"."{TABLE}"'
    print("=" * 60)
    print("Очистка Доп. расходов (manual_expenses)")
    print("=" * 60)
    print(f"Оставляем только даты: {', '.join(KEEP_DATES)}")
    print()

    with engine.connect() as conn:
        # Считаем, сколько записей будет удалено
        count_del = conn.execute(
            text(f"""
                SELECT COUNT(*) FROM {qname_table}
                WHERE expense_date::date NOT IN (
                    :d1, :d2, :d3, :d4
                )
            """),
            {
                "d1": KEEP_DATES[0],
                "d2": KEEP_DATES[1],
                "d3": KEEP_DATES[2],
                "d4": KEEP_DATES[3],
            },
        ).scalar()
        count_keep = conn.execute(
            text(f"""
                SELECT COUNT(*) FROM {qname_table}
                WHERE expense_date::date IN (
                    :d1, :d2, :d3, :d4
                )
            """),
            {
                "d1": KEEP_DATES[0],
                "d2": KEEP_DATES[1],
                "d3": KEEP_DATES[2],
                "d4": KEEP_DATES[3],
            },
        ).scalar()
        print(f"Будет удалено записей: {count_del}")
        print(f"Останется записей: {count_keep}")
        print()

        if count_del == 0:
            print("Нечего удалять. Выход.")
            return

        conn.execute(
            text(f"""
                DELETE FROM {qname_table}
                WHERE expense_date::date NOT IN (
                    :d1, :d2, :d3, :d4
                )
            """),
            {
                "d1": KEEP_DATES[0],
                "d2": KEEP_DATES[1],
                "d3": KEEP_DATES[2],
                "d4": KEEP_DATES[3],
            },
        )
        conn.commit()
        print("Готово. Записи удалены.")
    print("=" * 60)


if __name__ == "__main__":
    main()
