"""support_tickets: user appeals from Support «Создать обращение»

Revision ID: 20260411_support_tickets
Revises: 20260157
Create Date: 2026-04-11 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260411_support_tickets"
down_revision: Union[str, None] = "20260157"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.support_tickets (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
                subject varchar(500) NOT NULL,
                priority varchar(32) NOT NULL DEFAULT 'medium',
                category varchar(64) NOT NULL,
                description text NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_support_tickets_created_at
            ON {SCHEMA}.support_tickets (created_at DESC)
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_support_tickets_user_id
            ON {SCHEMA}.support_tickets (user_id)
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.support_tickets"))
