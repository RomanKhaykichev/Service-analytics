"""Apply pending migrations manually and stamp alembic head."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
load_dotenv()

SCHEMA = "app"
HEAD = "20260707_drop_trial_shop"
engine = create_engine(os.environ["DATABASE_URL"], connect_args={"connect_timeout": 10})

with engine.begin() as conn:
    current = conn.execute(text(f"SELECT version_num FROM {SCHEMA}.alembic_version")).scalar()
    print("current revision:", current)

    conn.execute(text(f"ALTER TABLE {SCHEMA}.stg_expenses ADD COLUMN IF NOT EXISTS shop_raw text"))
    conn.execute(text(f"ALTER TABLE {SCHEMA}.fact_expenses ADD COLUMN IF NOT EXISTS shop_raw text"))
    conn.execute(text(f"ALTER TABLE {SCHEMA}.fact_expenses ADD COLUMN IF NOT EXISTS shop_id uuid"))
    conn.execute(
        text(
            f"ALTER TABLE {SCHEMA}.fact_leftout_old_snapshot "
            "ADD COLUMN IF NOT EXISTS fbs_qty integer NOT NULL DEFAULT 0"
        )
    )
    conn.execute(
        text(
            f"ALTER TABLE {SCHEMA}.users "
            "ADD COLUMN IF NOT EXISTS trial_display_shop varchar(255)"
        )
    )

    rows = conn.execute(
        text(
            f"""
            SELECT id::text, trial_display_shop
            FROM {SCHEMA}.users
            WHERE trial_display_shop IS NOT NULL
              AND trim(trial_display_shop) <> ''
              AND (
                  allowed_shops IS NULL
                  OR trim(allowed_shops) = ''
                  OR allowed_shops = '[]'
              )
            """
        )
    ).fetchall()
    migrated = 0
    for uid, shop in rows or []:
        if not shop:
            continue
        payload = json.dumps([str(shop).strip()], ensure_ascii=False)
        conn.execute(
            text(f"UPDATE {SCHEMA}.users SET allowed_shops = :p WHERE id = CAST(:uid AS uuid)"),
            {"p": payload, "uid": uid},
        )
        migrated += 1
    print("migrated trial_display_shop rows:", migrated)

    conn.execute(text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN IF EXISTS trial_display_shop"))
    conn.execute(
        text(f"UPDATE {SCHEMA}.alembic_version SET version_num = :v"),
        {"v": HEAD},
    )
    print("stamped:", HEAD)

with engine.connect() as conn:
    col = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema=:s AND table_name='users' AND column_name='trial_display_shop'"
        ),
        {"s": SCHEMA},
    ).fetchone()
    rev = conn.execute(text(f"SELECT version_num FROM {SCHEMA}.alembic_version")).scalar()
    print("trial_display_shop column:", "yes" if col else "no")
    print("alembic revision:", rev)
