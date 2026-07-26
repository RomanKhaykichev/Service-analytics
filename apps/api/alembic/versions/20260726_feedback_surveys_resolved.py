"""feedback_surveys.resolved for admin mark-as-done

Revision ID: 20260726_feedback_surveys_resolved
Revises: 20260726_feedback_surveys
Create Date: 2026-07-26 00:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260726_feedback_surveys_resolved"
down_revision: Union[str, None] = "20260726_feedback_surveys"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.feedback_surveys
            ADD COLUMN IF NOT EXISTS resolved boolean NOT NULL DEFAULT false
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"ALTER TABLE {SCHEMA}.feedback_surveys DROP COLUMN IF EXISTS resolved"))
