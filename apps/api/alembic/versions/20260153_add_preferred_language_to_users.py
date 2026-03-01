"""add preferred_language to users for per-account UI language

Revision ID: 20260153
Revises: 20260152
Create Date: 2026-01-53 00:00:00.000000

- app.users: preferred_language varchar(10) nullable ('ru' | 'uz')
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260153"
down_revision: Union[str, None] = "20260152"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"
TABLE = "users"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.{TABLE}
        ADD COLUMN IF NOT EXISTS preferred_language varchar(10) NULL
    """))


def downgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.{TABLE}
        DROP COLUMN IF EXISTS preferred_language
    """))
