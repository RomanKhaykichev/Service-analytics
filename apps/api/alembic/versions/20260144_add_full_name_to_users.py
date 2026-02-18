"""add full_name to users

Revision ID: 20260144_add_full_name_users
Revises: 20260143_add_name_to_manual_expenses
Create Date: 2026-01-44 00:00:00.000000

- app.users: add column full_name varchar(255) nullable for display name
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260144_add_full_name_users"
down_revision: Union[str, None] = "20260143_auth_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"
TABLE = "users"
Q = f"{SCHEMA}.{TABLE}"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {Q}
        ADD COLUMN IF NOT EXISTS full_name varchar(255)
    """))


def downgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {Q}
        DROP COLUMN IF EXISTS full_name
    """))
