"""Migrate trial_display_shop into allowed_shops and drop column.

Revision ID: 20260707_drop_trial_shop
Revises: 20260706_trial_shop
"""
from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260707_drop_trial_shop"
down_revision: Union[str, None] = "20260706_trial_shop"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    conn = op.get_bind()
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
    for uid, shop in rows or []:
        if not shop:
            continue
        payload = json.dumps([str(shop).strip()], ensure_ascii=False)
        conn.execute(
            text(f"UPDATE {SCHEMA}.users SET allowed_shops = :p WHERE id = CAST(:uid AS uuid)"),
            {"p": payload, "uid": uid},
        )
    op.execute(
        text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN IF EXISTS trial_display_shop")
    )


def downgrade() -> None:
    op.execute(
        text(
            f"ALTER TABLE {SCHEMA}.users "
            "ADD COLUMN IF NOT EXISTS trial_display_shop varchar(255)"
        )
    )
