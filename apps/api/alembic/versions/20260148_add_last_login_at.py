"""add last_login_at to users for admin visits metric

Revision ID: 20260148
Revises: 20260147_admin
Create Date: 2026-01-48 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260148"
down_revision: Union[str, None] = "20260147_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.users
        ADD COLUMN IF NOT EXISTS last_login_at timestamptz
    """))


def downgrade() -> None:
    op.execute(text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN IF EXISTS last_login_at"))
