"""Debug script for user shop/data state (fast queries only)."""
from app.db import SessionLocal
from app.settings import get_settings
from sqlalchemy import text

EMAIL = "test_19b3197f8ded@example.com"


def main() -> None:
    db = SessionLocal()
    s = get_settings()
    schema = s.DB_SCHEMA
    db.execute(text(f"SET search_path TO {schema}, public"))

    row = db.execute(
        text(
            f"""
            SELECT id::text, plan, trial_ends_at, allowed_shops, is_active,
                   trial_ends_at > now() AS trial_active
            FROM {schema}.users WHERE email = :e
            """
        ),
        {"e": EMAIL},
    ).fetchone()
    if not row:
        print("USER NOT FOUND")
        return

    uid = row[0]
    print("user", uid, "plan", row[1], "trial_active", row[5])
    print("allowed_shops", row[3])

    dim = db.execute(
        text(
            f"""
            SELECT shop_name, api_key_accessible
            FROM {schema}.dim_shop
            WHERE user_id = CAST(:u AS uuid)
            ORDER BY shop_name
            """
        ),
        {"u": uid},
    ).fetchall()
    print("dim_shop", dim)

    storage = db.execute(
        text(
            f"""
            SELECT COUNT(*) AS cnt,
                   COUNT(DISTINCT upper(regexp_replace(trim(shop_raw), '\\s+', ' ', 'g'))) AS shops
            FROM {schema}.fact_storage_snapshot
            WHERE user_id = CAST(:u AS uuid)
            """
        ),
        {"u": uid},
    ).fetchone()
    print("fact_storage_snapshot", "rows", storage[0], "shops", storage[1])

    storage_shops = db.execute(
        text(
            f"""
            SELECT DISTINCT upper(regexp_replace(trim(shop_raw), '\\s+', ' ', 'g')) AS shop_norm
            FROM {schema}.fact_storage_snapshot
            WHERE user_id = CAST(:u AS uuid)
              AND shop_raw IS NOT NULL
            LIMIT 20
            """
        ),
        {"u": uid},
    ).fetchall()
    print("storage shop_norms", [r[0] for r in storage_shops])

    sales = db.execute(
        text(
            f"""
            SELECT COUNT(*) FROM {schema}.fact_sales
            WHERE user_id = CAST(:u AS uuid)
            """
        ),
        {"u": uid},
    ).scalar()
    print("fact_sales rows", sales)

    syncs = db.execute(
        text(
            f"""
            SELECT status, trigger, started_at, finished_at, error_message
            FROM {schema}.uzum_sync_log
            WHERE user_id = CAST(:u AS uuid)
            ORDER BY started_at DESC NULLS LAST
            LIMIT 8
            """
        ),
        {"u": uid},
    ).fetchall()
    print("sync logs:")
    for srow in syncs:
        print(" ", srow)

    db.close()


if __name__ == "__main__":
    main()
