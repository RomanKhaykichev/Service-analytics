"""feedback_surveys: client feedback questionnaire submissions

Revision ID: 20260726_feedback_surveys
Revises: 20260715_stg_leftout_old_row_num
Create Date: 2026-07-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260726_feedback_surveys"
down_revision: Union[str, None] = "20260715_stg_leftout_old_row_num"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.feedback_surveys (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
                answers jsonb NOT NULL,
                nps smallint,
                helpfulness smallint,
                client_name varchar(255),
                client_contact varchar(255),
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_feedback_surveys_created_at
            ON {SCHEMA}.feedback_surveys (created_at DESC)
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_feedback_surveys_user_id
            ON {SCHEMA}.feedback_surveys (user_id)
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.feedback_surveys"))
