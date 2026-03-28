"""index on pending_registrations.expires_at for cleanup deletes

Revision ID: 20260157
Revises: 20260156
Create Date: 2026-03-28 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260157"
down_revision: Union[str, None] = "20260156"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_pending_registrations_expires_at
            ON {SCHEMA}.pending_registrations (expires_at)
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_pending_registrations_expires_at"))
