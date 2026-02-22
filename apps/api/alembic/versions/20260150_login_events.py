"""login_events table for total visits per day (общее количество заходов)

Revision ID: 20260150
Revises: 20260149
Create Date: 2026-01-50 00:00:00.000000

- app.login_events: каждый вход на сайт (user_id, logged_at) для метрики «Посещения».
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260150"
down_revision: Union[str, None] = "20260149"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.login_events (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            logged_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_login_events_logged_at ON {SCHEMA}.login_events (logged_at)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_login_events_user_id ON {SCHEMA}.login_events (user_id)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.login_events"))
