"""add cost_per_unit and price_per_unit to leftout_old for Склад metrics

Revision ID: 20260134_leftout_old_cost_price
Revises: 20260133_ensure_leftout_old
Create Date: 2026-01-34 00:00:00.000000

- stg_leftout_old: cost_per_unit_raw text, price_per_unit_raw text
- fact_leftout_old_snapshot: cost_per_unit numeric(18,2), price_per_unit numeric(18,2)
  (Себест. (сумы), Стоимость продажи (сумы) за единицу)
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260134_leftout_old_cost_price"
down_revision: Union[str, None] = "20260133_ensure_leftout_old"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.stg_leftout_old
        ADD COLUMN IF NOT EXISTS cost_per_unit_raw text,
        ADD COLUMN IF NOT EXISTS price_per_unit_raw text
    """))
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.fact_leftout_old_snapshot
        ADD COLUMN IF NOT EXISTS cost_per_unit numeric(18,2),
        ADD COLUMN IF NOT EXISTS price_per_unit numeric(18,2)
    """))


def downgrade() -> None:
    op.execute(text(f"ALTER TABLE {SCHEMA}.fact_leftout_old_snapshot DROP COLUMN IF EXISTS price_per_unit, DROP COLUMN IF EXISTS cost_per_unit"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.stg_leftout_old DROP COLUMN IF EXISTS price_per_unit_raw, DROP COLUMN IF EXISTS cost_per_unit_raw"))
