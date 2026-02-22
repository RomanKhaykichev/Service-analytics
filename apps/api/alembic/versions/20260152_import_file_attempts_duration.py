"""add duration_seconds to import_file_attempts for average upload time metric

Revision ID: 20260152
Revises: 20260151
Create Date: 2026-01-52 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260152"
down_revision: Union[str, None] = "20260151"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.import_file_attempts
        ADD COLUMN IF NOT EXISTS duration_seconds numeric NULL
    """))


def downgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.import_file_attempts
        DROP COLUMN IF EXISTS duration_seconds
    """))
