"""Compare daily profit components pa vs romanx on 2026-05-23 and 2026-05-24."""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ.get("DATABASE_URL", ""))
schema = os.environ.get("DB_SCHEMA", "app")

USERS = {
    "pa@mail.ru": "edef8fcb-177f-4412-9a3c-dc3be0ef0681",
    "mr.romanx@mail.ru": "8a2e71de-52a3-4eeb-a868-df9f7ff7c9b8",
}
DAY_S = "(fs.date_created::date)"
DAY_E = "(date_written_off AT TIME ZONE 'Asia/Tashkent')::date"

REV_COND = """
    (lower(trim(fs.status)) IN ('завершен', 'завершён', 'в обработке')
     OR lower(trim(fs.status)) LIKE '%yetkazilgan%'
     OR lower(trim(fs.status)) LIKE '%qayta ishlashda%'
     OR lower(trim(fs.status)) LIKE '%qayta ishlanmoqda%')
"""


def main() -> None:
    with engine.connect() as conn:
        for dt in ("2026-05-23", "2026-05-24"):
            print(f"\n========== {dt} ==========")
            for email, uid in USERS.items():
                sales = conn.execute(
                    text(
                        f"""
                        SELECT
                          COUNT(*),
                          COALESCE(SUM(CASE WHEN {REV_COND} THEN revenue_sum ELSE 0 END), 0),
                          COALESCE(SUM(CASE WHEN {REV_COND} THEN commission_sum ELSE 0 END), 0),
                          COALESCE(SUM(CASE WHEN {REV_COND} THEN logistics_sum ELSE 0 END), 0),
                          COALESCE(SUM(CASE WHEN {REV_COND} THEN cogs_sum * qty ELSE 0 END), 0)
                        FROM {schema}.fact_sales fs
                        WHERE fs.user_id = CAST(:u AS uuid)
                          AND {DAY_S} = CAST(:d AS date)
                        """
                    ),
                    {"u": uid, "d": dt},
                ).fetchone()
                exp = conn.execute(
                    text(
                        f"""
                        SELECT
                          COALESCE(SUM(CASE
                            WHEN upper(trim(source)) = 'СКЛАД' AND upper(trim(operation_type)) = 'ОПЛАТА' THEN cost_sum
                            WHEN upper(trim(source)) = 'СКЛАД' AND upper(trim(operation_type)) = 'ВОЗВРАТ' THEN -cost_sum
                            ELSE 0 END), 0),
                          COALESCE(SUM(CASE
                            WHEN upper(trim(source)) = 'МАРКЕТИНГ' AND upper(trim(operation_type)) = 'ОПЛАТА' THEN cost_sum
                            WHEN upper(trim(source)) = 'МАРКЕТИНГ' AND upper(trim(operation_type)) = 'ВОЗВРАТ' THEN -cost_sum
                            ELSE 0 END), 0)
                        FROM {schema}.fact_expenses fe
                        WHERE fe.user_id = CAST(:u AS uuid) AND {DAY_E} = CAST(:d AS date)
                        """
                    ),
                    {"u": uid, "d": dt},
                ).fetchone()
                rev, comm, logi, cogs = float(sales[1]), float(sales[2]), float(sales[3]), float(sales[4])
                storage, ads = float(exp[0]), float(exp[1])
                tax = round(rev * 0.01, 2)
                profit = rev - comm - logi - storage - ads - cogs - tax
                print(f"\n{email}:")
                print(f"  sales rows={sales[0]} revenue={rev:,.0f} comm={comm:,.0f} log={logi:,.0f} cogs={cogs:,.0f}")
                print(f"  storage={storage:,.0f} ads={ads:,.0f} tax(1%)={tax:,.0f}")
                print(f"  profit={profit:,.0f}")

        print("\n========== Profit diff = storage diff ==========")
        print("  23.05: storage pa 36,960 vs api 44,960 -> profit -8,000 on api")
        print("  24.05: storage pa 45,310 vs api 37,310 -> profit +8,000 on api")


def storage_by_day() -> None:
    with engine.connect() as conn:
        for dt in ("2026-05-22", "2026-05-23", "2026-05-24", "2026-05-25"):
            print(f"\n--- storage {dt} ---")
            for email, uid in USERS.items():
                rows = conn.execute(
                    text(
                        f"""
                        SELECT operation_id, cost_sum
                        FROM {schema}.fact_expenses
                        WHERE user_id = CAST(:u AS uuid)
                          AND {DAY_E} = CAST(:d AS date)
                          AND upper(trim(source)) = 'СКЛАД'
                          AND upper(trim(operation_type)) = 'ОПЛАТА'
                        ORDER BY operation_id
                        """
                    ),
                    {"u": uid, "d": dt},
                ).fetchall()
                total = sum(float(r[1]) for r in rows)
                print(f"  {email}: n={len(rows)} sum={total:,.0f} ids={[r[0] for r in rows]}")


if __name__ == "__main__":
    main()
    storage_by_day()
