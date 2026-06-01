"""Daily storage/ads by UZ calendar day + sample written_off dates."""
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

DAY_EXPR = "(date_written_off AT TIME ZONE 'Asia/Tashkent')::date"


def main() -> None:
    with engine.connect() as conn:
        for email, uid in USERS.items():
            print(f"\n=== {email} daily storage/ads (May 1-7) ===")
            rows = conn.execute(
                text(
                    f"""
                    SELECT
                      {DAY_EXPR} AS day,
                      COALESCE(SUM(CASE
                        WHEN upper(trim(source)) = 'СКЛАД' AND upper(trim(operation_type)) = 'ОПЛАТА' THEN cost_sum
                        WHEN upper(trim(source)) = 'СКЛАД' AND upper(trim(operation_type)) = 'ВОЗВРАТ' THEN -cost_sum
                        ELSE 0 END), 0) AS storage,
                      COALESCE(SUM(CASE
                        WHEN upper(trim(source)) = 'МАРКЕТИНГ' AND upper(trim(operation_type)) = 'ОПЛАТА' THEN cost_sum
                        WHEN upper(trim(source)) = 'МАРКЕТИНГ' AND upper(trim(operation_type)) = 'ВОЗВРАТ' THEN -cost_sum
                        ELSE 0 END), 0) AS ads
                    FROM {schema}.fact_expenses
                    WHERE user_id = CAST(:uid AS uuid)
                      AND date_written_off >= '2026-05-01'
                      AND date_written_off < '2026-05-08'
                    GROUP BY 1
                    ORDER BY 1
                    """
                ),
                {"uid": uid},
            ).fetchall()
            for r in rows:
                print(f"  {r[0]}: storage={float(r[1]):,.0f} ads={float(r[2]):,.0f}")

            print("  Sample rows (storage+marketing, May 1-3):")
            samples = conn.execute(
                text(
                    f"""
                    SELECT operation_id, service, cost_sum,
                           date_written_off,
                           {DAY_EXPR} AS uz_day
                    FROM {schema}.fact_expenses
                    WHERE user_id = CAST(:uid AS uuid)
                      AND upper(trim(source)) IN ('СКЛАД', 'МАРКЕТИНГ')
                      AND date_written_off >= '2026-05-01'
                      AND date_written_off < '2026-05-04'
                    ORDER BY date_written_off, operation_id
                    LIMIT 8
                    """
                ),
                {"uid": uid},
            ).fetchall()
            for s in samples:
                print(f"    id={s[0]} svc={s[1]!r} cost={s[2]} ts={s[3]} uz_day={s[4]}")

        # stg raw if any
        for email, uid in USERS.items():
            cnt = conn.execute(
                text(
                    f"SELECT COUNT(*) FROM {schema}.stg_expenses WHERE user_id = CAST(:uid AS uuid)"
                ),
                {"uid": uid},
            ).scalar()
            if not cnt:
                continue
            print(f"\n=== {email} stg written_off for op 147029297 ===")
            raw = conn.execute(
                text(
                    f"""
                    SELECT written_off_raw, cost_raw, operation_id_raw
                    FROM {schema}.stg_expenses
                    WHERE user_id = CAST(:uid AS uuid)
                      AND operation_id_raw = '147029297'
                    """
                ),
                {"uid": uid},
            ).fetchall()
            for r in raw:
                print(f"  {r[0]!r} cost={r[1]} id={r[2]}")


if __name__ == "__main__":
    main()
