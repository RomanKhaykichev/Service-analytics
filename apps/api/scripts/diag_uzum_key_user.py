"""Diagnose Uzum API key access for a user (sync logs + live probe)."""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

USERS = {
    "pa@mail.ru": "edef8fcb-177f-4412-9a3c-dc3be0ef0681",
}

schema = os.environ.get("DB_SCHEMA", "app")
engine = create_engine(os.environ.get("DATABASE_URL", ""))


def main() -> None:
    email = sys.argv[1] if len(sys.argv) > 1 else "pa@mail.ru"
    uid = USERS.get(email)
    if not uid:
        print(f"Unknown user {email}")
        sys.exit(1)
    if not os.environ.get("DATABASE_URL"):
        print("Set DATABASE_URL")
        sys.exit(1)

    from app.services.uzum_api_helpers import validate_api_key_access

    with engine.connect() as conn:
        row = conn.execute(
            text(f"""
                SELECT uzum_seller_api_key IS NOT NULL AS has_key,
                       left(coalesce(uzum_seller_api_key, ''), 8) AS key_prefix
                FROM {schema}.users
                WHERE id = CAST(:uid AS uuid)
            """),
            {"uid": uid},
        ).fetchone()
        print(f"User: {email} ({uid})")
        print(f"Has API key: {row[0]}, prefix: {row[1]}…")

        logs = conn.execute(
            text(f"""
                SELECT status, trigger, started_at, finished_at,
                       error_message, left(coalesce(error_detail, ''), 400) AS detail
                FROM {schema}.uzum_sync_log
                WHERE user_id = CAST(:uid AS uuid)
                ORDER BY started_at DESC
                LIMIT 5
            """),
            {"uid": uid},
        ).fetchall()
        print("\nLast sync logs:")
        for log in logs:
            print(log)

        key_row = conn.execute(
            text(f"""
                SELECT uzum_seller_api_key FROM {schema}.users
                WHERE id = CAST(:uid AS uuid)
            """),
            {"uid": uid},
        ).fetchone()
        api_key = (key_row[0] or "").strip() if key_row else ""
        if not api_key:
            print("\nNo saved API key — pass key as 2nd arg to probe live.")
            if len(sys.argv) < 3:
                return
            api_key = sys.argv[2].strip()
        elif len(sys.argv) >= 3:
            api_key = sys.argv[2].strip()

    print("\nLive validate_api_key_access:")
    result = validate_api_key_access(api_key)
    print(f"  ok={result.ok} shop_ids={result.shop_ids} error={result.error}")
    for probe in result.probes:
        print(
            f"  shop {probe.shop_id}: product={probe.product_ok} "
            f"orders={probe.orders_ok} expenses={probe.expenses_ok}"
        )
        for err in probe.errors:
            print(f"    - {err}")


if __name__ == "__main__":
    main()
