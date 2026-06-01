"""Compare May 2026 metrics between pa@mail.ru and mr.romanx@mail.ru."""
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.environ.get("DATABASE_URL", ""))
schema = os.environ.get("DB_SCHEMA", "app")

USERS = {
    "pa@mail.ru": "edef8fcb-177f-4412-9a3c-dc3be0ef0681",
    "mr.romanx@mail.ru": "8a2e71de-52a3-4eeb-a868-df9f7ff7c9b8",
}
DATE_FROM = "2026-05-01"
DATE_TO = "2026-05-31"

REV_COND = """
    (lower(trim(status)) IN ('завершен', 'завершён')
     OR lower(trim(status)) = 'в обработке'
     OR lower(trim(status)) LIKE '%yetkazilgan%'
     OR lower(trim(status)) LIKE '%yakunlangan%'
     OR lower(trim(status)) LIKE '%yakunlandi%'
     OR lower(trim(status)) LIKE '%qayta ishlashda%'
     OR lower(trim(status)) LIKE '%qayta ishlanmoqda%'
     OR lower(trim(status)) LIKE '%jarayonda%')
"""


def main() -> None:
    with engine.connect() as conn:
        for email, uid in USERS.items():
            print(f"\n=== {email} ===")
            row = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*), COALESCE(SUM(revenue_sum), 0), COALESCE(SUM(qty), 0)
                    FROM {schema}.fact_sales
                    WHERE user_id = CAST(:uid AS uuid)
                      AND date_created >= CAST(:df AS date)
                      AND date_created < CAST(:dt AS date) + interval '1 day'
                    """
                ),
                {"uid": uid, "df": DATE_FROM, "dt": DATE_TO},
            ).fetchone()
            print(f"Sales rows: {row[0]}, sum(revenue): {float(row[1]):,.0f}, sum(qty): {row[2]}")

            kpi_rev = conn.execute(
                text(
                    f"""
                    SELECT COALESCE(SUM(CASE WHEN {REV_COND} THEN revenue_sum ELSE 0 END), 0)
                    FROM {schema}.fact_sales
                    WHERE user_id = CAST(:uid AS uuid)
                      AND date_created >= CAST(:df AS date)
                      AND date_created < CAST(:dt AS date) + interval '1 day'
                    """
                ),
                {"uid": uid, "df": DATE_FROM, "dt": DATE_TO},
            ).scalar()
            print(f"KPI revenue (completed+processing only): {float(kpi_rev):,.0f}")

            statuses = conn.execute(
                text(
                    f"""
                    SELECT lower(trim(status)), COUNT(*), COALESCE(SUM(revenue_sum), 0)
                    FROM {schema}.fact_sales
                    WHERE user_id = CAST(:uid AS uuid)
                      AND date_created >= CAST(:df AS date)
                      AND date_created < CAST(:dt AS date) + interval '1 day'
                    GROUP BY 1
                    ORDER BY 2 DESC
                    """
                ),
                {"uid": uid, "df": DATE_FROM, "dt": DATE_TO},
            ).fetchall()
            print("By status:")
            for st, cnt, rev in statuses:
                print(f"  {st!r}: rows={cnt}, revenue={float(rev or 0):,.0f}")

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
                        WHEN upper(trim(operation_type)) = 'ВОЗВРАТ' AND upper(trim(source)) = 'МАРКЕТИНГ' THEN -cost_sum
                        ELSE 0 END), 0),
                      COUNT(*),
                      MIN(date_written_off::date),
                      MAX(date_written_off::date)
                    FROM {schema}.fact_expenses
                    WHERE user_id = CAST(:uid AS uuid)
                      AND date_written_off >= CAST(:df AS date)
                      AND date_written_off < CAST(:dt AS date) + interval '1 day'
                    """
                ),
                {"uid": uid, "df": DATE_FROM, "dt": DATE_TO},
            ).fetchone()
            print(
                f"Expenses May: storage={float(exp[0]):,.0f}, ads={float(exp[1]):,.0f}, "
                f"rows={exp[2]}, dates {exp[3]}..{exp[4]}"
            )

            apr30 = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*), COALESCE(SUM(cost_sum), 0)
                    FROM {schema}.fact_expenses
                    WHERE user_id = CAST(:uid AS uuid)
                      AND date_written_off::date = '2026-04-30'
                    """
                ),
                {"uid": uid},
            ).fetchone()
            print(f"Expenses on 2026-04-30 (outside May): rows={apr30[0]}, sum={float(apr30[1] or 0):,.0f}")

            storage_rows = conn.execute(
                text(
                    f"""
                    SELECT COUNT(*) FROM {schema}.fact_storage_snapshot
                    WHERE user_id = CAST(:uid AS uuid)
                    """
                ),
                {"uid": uid},
            ).scalar()
            print(f"Storage snapshot rows (all time): {storage_rows}")

            extra = conn.execute(
                text(
                    f"""
                    SELECT
                      COALESCE(SUM(CASE WHEN {REV_COND} THEN commission_sum ELSE 0 END), 0),
                      COALESCE(SUM(CASE WHEN {REV_COND} THEN logistics_sum ELSE 0 END), 0),
                      COALESCE(SUM(CASE WHEN {REV_COND} THEN cogs_sum * qty ELSE 0 END), 0),
                      COALESCE(SUM(CASE WHEN {REV_COND} THEN qty ELSE 0 END), 0),
                      COUNT(DISTINCT order_no)
                    FROM {schema}.fact_sales
                    WHERE user_id = CAST(:uid AS uuid)
                      AND date_created >= CAST(:df AS date)
                      AND date_created < CAST(:dt AS date) + interval '1 day'
                    """
                ),
                {"uid": uid, "df": DATE_FROM, "dt": DATE_TO},
            ).fetchone()
            print(
                f"KPI extras: commission={float(extra[0]):,.0f}, logistics={float(extra[1]):,.0f}, "
                f"cogs={float(extra[2]):,.0f}, buyout_qty={extra[3]}, distinct_orders={extra[4]}"
            )

            # Rows only in one account by order_no+barcode (if same shops - rough)
            missing_rev = conn.execute(
                text(
                    f"""
                    SELECT COALESCE(SUM(revenue_sum),0), COUNT(*)
                    FROM {schema}.fact_sales
                    WHERE user_id = CAST(:uid AS uuid)
                      AND date_created >= CAST(:df AS date)
                      AND date_created < CAST(:dt AS date) + interval '1 day'
                      AND COALESCE(revenue_sum, 0) = 0 AND qty > 0
                    """
                ),
                {"uid": uid, "df": DATE_FROM, "dt": DATE_TO},
            ).fetchone()
            print(f"Rows with qty>0 but revenue=0: count={missing_rev[1]}")

            shops = conn.execute(
                text(
                    f"""
                    SELECT ds.shop_name, COUNT(*) 
                    FROM {schema}.fact_sales fs
                    JOIN {schema}.dim_shop ds ON ds.id = fs.shop_id
                    WHERE fs.user_id = CAST(:uid AS uuid)
                      AND fs.date_created >= CAST(:df AS date)
                      AND fs.date_created < CAST(:dt AS date) + interval '1 day'
                    GROUP BY 1 ORDER BY 2 DESC
                    """
                ),
                {"uid": uid, "df": DATE_FROM, "dt": DATE_TO},
            ).fetchall()
            print(f"Shops in sales ({len(shops)}):")
            for name, cnt in shops[:8]:
                print(f"  {name}: {cnt}")


if __name__ == "__main__":
    main()
