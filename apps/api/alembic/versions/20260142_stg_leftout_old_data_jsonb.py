"""Add data jsonb to app.stg_leftout_old (full row as dict for left-out-report_old).

Revision ID: 20260142_stg_old_data
Revises: 20260141_leftout_old
Create Date: 2026-01-42

- app.stg_leftout_old: add column data jsonb (entire row as dict).
- Keeps barcode_raw, in_sale_raw, cost_raw, price_raw.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260142_stg_old_data"
down_revision: Union[str, None] = "20260141_leftout_old"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.stg_leftout_old
        ADD COLUMN IF NOT EXISTS data jsonb
    """))


def downgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.stg_leftout_old
        DROP COLUMN IF EXISTS data
    """))
