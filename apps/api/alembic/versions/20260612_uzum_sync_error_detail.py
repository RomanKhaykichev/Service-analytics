"""uzum_sync_log: error_detail for full error text

Revision ID: 20260612_sync_err
Revises: 20260528_uzum_sync
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260612_sync_err"
down_revision: Union[str, None] = "20260528_uzum_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.uzum_sync_log
        ADD COLUMN IF NOT EXISTS error_detail text NULL
    """))


def downgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.uzum_sync_log
        DROP COLUMN IF EXISTS error_detail
    """))
