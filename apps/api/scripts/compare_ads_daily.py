"""Compare daily ads (Маркетинг) between pa@mail.ru and mr.romanx@mail.ru."""
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
DAY = "(date_written_off AT TIME ZONE 'Asia/Tashkent')::date"
ADS = """
  COALESCE(SUM(CASE
    WHEN upper(trim(source)) = 'МАРКЕТИНГ' AND upper(trim(operation_type)) = 'ОПЛАТА' THEN cost_sum
    WHEN upper(trim(source)) = 'МАРКЕТИНГ' AND upper(trim(operation_type)) = 'ВОЗВРАТ' THEN -cost_sum
    ELSE 0 END), 0)
"""


def main() -> None:
    with engine.connect() as conn:
        print("=== Daily ads May 2026 ===")
        for email, uid in USERS.items():
            rows = conn.execute(
                text(
                    f"""
                    SELECT {DAY} AS d, {ADS} AS ads, COUNT(*) AS n
                    FROM {schema}.fact_expenses
                    WHERE user_id = CAST(:uid AS uuid)
                      AND date_written_off >= '2026-05-01'
                      AND date_written_off < '2026-06-01'
                      AND upper(trim(source)) = 'МАРКЕТИНГ'
                    GROUP BY 1 ORDER BY 1
                    """
                ),
                {"uid": uid},
            ).fetchall()
            print(f"\n{email}:")
            for r in rows:
                print(f"  {r[0]}: ads={float(r[1]):,.0f} rows={r[2]}")

        print("\n=== Dates with largest |diff| ===")
        pa = {
            r[0]: float(r[1])
            for r in conn.execute(
                text(
                    f"SELECT {DAY}, {ADS} FROM {schema}.fact_expenses "
                    f"WHERE user_id = CAST(:u AS uuid) AND date_written_off >= '2026-05-01' "
                    f"AND date_written_off < '2026-06-01' GROUP BY 1"
                ),
                {"u": USERS["pa@mail.ru"]},
            )
        }
        mx = {
            r[0]: float(r[1])
            for r in conn.execute(
                text(
                    f"SELECT {DAY}, {ADS} FROM {schema}.fact_expenses "
                    f"WHERE user_id = CAST(:u AS uuid) AND date_written_off >= '2026-05-01' "
                    f"AND date_written_off < '2026-06-01' GROUP BY 1"
                ),
                {"u": USERS["mr.romanx@mail.ru"]},
            )
        }
        for d in sorted(set(pa) | set(mx)):
            if d.month != 5:
                continue
            diff = pa.get(d, 0) - mx.get(d, 0)
            if abs(diff) > 100:
                print(f"  {d}: pa={pa.get(d,0):,.0f} romanx={mx.get(d,0):,.0f} diff={diff:,.0f}")

        for target in ("2026-05-04", "2026-05-06", "2026-05-21"):
            print(f"\n=== {target} operation_ids only in one account ===")
            for label, uid in USERS.items():
                other = USERS["pa@mail.ru"] if uid == USERS["mr.romanx@mail.ru"] else USERS["mr.romanx@mail.ru"]
                only = conn.execute(
                    text(
                        f"""
                        SELECT a.operation_id, a.cost_sum, a.operation_type,
                               left(a.service, 60), a.date_written_off
                        FROM {schema}.fact_expenses a
                        WHERE a.user_id = CAST(:uid AS uuid)
                          AND {DAY} = CAST(:d AS date)
                          AND upper(trim(a.source)) = 'МАРКЕТИНГ'
                          AND NOT EXISTS (
                            SELECT 1 FROM {schema}.fact_expenses b
                            WHERE b.user_id = CAST(:other AS uuid)
                              AND b.operation_id = a.operation_id
                          )
                        ORDER BY a.cost_sum DESC
                        LIMIT 15
                        """
                    ),
                    {"uid": uid, "other": other, "d": target},
                ).fetchall()
                print(f"  Only in {label}: {len(only)} shown (top 15)")
                for row in only:
                    print(f"    id={row[0]} cost={row[1]} type={row[2]} svc={row[3]!r}")

            both = conn.execute(
                text(
                    f"""
                    SELECT a.operation_id, a.cost_sum AS pa_cost, b.cost_sum AS mx_cost,
                           a.operation_type AS pa_type, b.operation_type AS mx_type
                    FROM {schema}.fact_expenses a
                    JOIN {schema}.fact_expenses b
                      ON b.user_id = CAST(:mx AS uuid) AND b.operation_id = a.operation_id
                    WHERE a.user_id = CAST(:pa AS uuid)
                      AND {DAY.replace('date_written_off', 'a.date_written_off')} = CAST(:d AS date)
                      AND upper(trim(a.source)) = 'МАРКЕТИНГ'
                      AND (a.cost_sum IS DISTINCT FROM b.cost_sum
                           OR upper(trim(a.operation_type)) IS DISTINCT FROM upper(trim(b.operation_type))
                           OR ({DAY.replace('date_written_off', 'a.date_written_off')})
                               IS DISTINCT FROM ({DAY.replace('date_written_off', 'b.date_written_off')}))
                    LIMIT 10
                    """
                ),
                {"pa": USERS["pa@mail.ru"], "mx": USERS["mr.romanx@mail.ru"], "d": target},
            ).fetchall()
            if both:
                print(f"  Same op_id, different cost/type/day: {len(both)}")
                for row in both:
                    print(f"    id={row[0]} pa={row[1]} mx={row[2]} types {row[3]}/{row[4]}")


def drill_shifted_ops() -> None:
    day = "(date_written_off AT TIME ZONE 'Asia/Tashkent')::date"
    ids = ["147666877", "152636928"]
    with engine.connect() as conn:
        for oid in ids:
            print(f"\n--- op {oid} ---")
            for email, uid in USERS.items():
                rows = conn.execute(
                    text(
                        f"""
                        SELECT operation_id, {day}, cost_sum, operation_type, left(service, 70)
                        FROM {schema}.fact_expenses
                        WHERE user_id = CAST(:u AS uuid) AND operation_id = :oid
                        """
                    ),
                    {"u": uid, "oid": oid},
                ).fetchall()
                print(f"  {email}: {rows}")
        for dt in ("2026-05-04", "2026-05-05", "2026-05-06", "2026-05-21", "2026-05-22"):
            print(f"\n--- marketing {dt} ---")
            for email, uid in USERS.items():
                rows = conn.execute(
                    text(
                        f"""
                        SELECT operation_id, cost_sum, operation_type
                        FROM {schema}.fact_expenses
                        WHERE user_id = CAST(:u AS uuid) AND {day} = CAST(:dt AS date)
                          AND upper(trim(source)) = 'МАРКЕТИНГ'
                        ORDER BY operation_id
                        """
                    ),
                    {"u": uid, "dt": dt},
                ).fetchall()
                print(f"  {email}: {[(r[0], float(r[1]), r[2]) for r in rows]}")


def marketing_timestamps() -> None:
    day = "(date_written_off AT TIME ZONE 'Asia/Tashkent')::date"
    with engine.connect() as conn:
        for oid in ("147666877", "147948412", "152636928"):
            print(f"\n--- timestamps {oid} ---")
            for email, uid in USERS.items():
                row = conn.execute(
                    text(
                        f"""
                        SELECT date_written_off,
                               date_written_off AT TIME ZONE 'Asia/Tashkent' AS uz_ts,
                               {day}
                        FROM {schema}.fact_expenses
                        WHERE user_id = CAST(:u AS uuid) AND operation_id = :oid
                        """
                    ),
                    {"u": uid, "oid": oid},
                ).fetchone()
                print(f"  {email}: {row}")


if __name__ == "__main__":
    main()
    drill_shifted_ops()
    marketing_timestamps()
