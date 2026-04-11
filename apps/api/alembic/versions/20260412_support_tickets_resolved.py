"""support_tickets.resolved for admin mark-as-done

Revision ID: 20260412_support_resolved
Revises: 20260411_support_tickets
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260412_support_resolved"
down_revision: Union[str, None] = "20260411_support_tickets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.support_tickets
            ADD COLUMN IF NOT EXISTS resolved boolean NOT NULL DEFAULT false
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"ALTER TABLE {SCHEMA}.support_tickets DROP COLUMN IF EXISTS resolved"))
