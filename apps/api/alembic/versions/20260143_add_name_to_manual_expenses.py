"""add name column to manual_expenses

Revision ID: 20260143_add_name_to_manual_expenses
Revises: 20260142_stg_old_data
Create Date: 2026-01-43 00:00:00.000000

- app.manual_expenses: add column name text (nullable) for product name from left-out-report_old
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260143_add_name_to_manual_expenses"
down_revision: Union[str, None] = "20260142_stg_old_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"
TABLE = "manual_expenses"
Q = f"{SCHEMA}.{TABLE}"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {Q}
        ADD COLUMN IF NOT EXISTS name text
    """))


def downgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {Q}
        DROP COLUMN IF EXISTS name
    """))
