"""fact_expenses and stg_expenses: shop_raw, shop_id for per-shop Uzum services filter

Revision ID: 20260628_exp_shop
Revises: 20260612_sync_err
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260628_exp_shop"
down_revision: Union[str, None] = "20260612_sync_err"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    # Staging/fact tables come from db/ SQL or ensure_import_tables.py, not this chain.
    op.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF to_regclass('{SCHEMA}.stg_expenses') IS NOT NULL THEN
                    ALTER TABLE {SCHEMA}.stg_expenses ADD COLUMN IF NOT EXISTS shop_raw text;
                END IF;
                IF to_regclass('{SCHEMA}.fact_expenses') IS NOT NULL THEN
                    ALTER TABLE {SCHEMA}.fact_expenses ADD COLUMN IF NOT EXISTS shop_raw text;
                    ALTER TABLE {SCHEMA}.fact_expenses ADD COLUMN IF NOT EXISTS shop_id uuid;
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"ALTER TABLE {SCHEMA}.fact_expenses DROP COLUMN IF EXISTS shop_id"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.fact_expenses DROP COLUMN IF EXISTS shop_raw"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.stg_expenses DROP COLUMN IF EXISTS shop_raw"))
