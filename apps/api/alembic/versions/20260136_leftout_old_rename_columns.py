"""leftout_old: rename fact_leftout_old_snapshot columns to in_sale_qty, cost_sum, price_sum

Revision ID: 20260136_leftout_old_cols
Revises: 20260135_leftout_old_user
Create Date: 2026-01-36 00:00:00.000000

- fact_leftout_old_snapshot: in_sale -> in_sale_qty, cost_per_unit -> cost_sum, price_per_unit -> price_sum
  (Товаров на складе = SUM(in_sale_qty), Себест. тов. = SUM(in_sale_qty * cost_sum), Рознич. цена = SUM(in_sale_qty * price_sum))
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260136_leftout_old_cols"
down_revision: Union[str, None] = "20260135_leftout_old_user"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"
TABLE = "fact_leftout_old_snapshot"


def upgrade() -> None:
    op.execute(text(f"ALTER TABLE {SCHEMA}.{TABLE} RENAME COLUMN in_sale TO in_sale_qty"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.{TABLE} RENAME COLUMN cost_per_unit TO cost_sum"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.{TABLE} RENAME COLUMN price_per_unit TO price_sum"))


def downgrade() -> None:
    op.execute(text(f"ALTER TABLE {SCHEMA}.{TABLE} RENAME COLUMN in_sale_qty TO in_sale"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.{TABLE} RENAME COLUMN cost_sum TO cost_per_unit"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.{TABLE} RENAME COLUMN price_sum TO price_per_unit"))
