"""uzum scheduled sync: last_api_sync_at + uzum_sync_log

Revision ID: 20260528_uzum_sync
Revises: 20260414_uzum_key
Create Date: 2026-05-28

- app.users: last_api_sync_at timestamptz NULL
- app.uzum_sync_log: audit log for scheduled/manual API sync runs
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260528_uzum_sync"
down_revision: Union[str, None] = "20260414_uzum_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.users
        ADD COLUMN IF NOT EXISTS last_api_sync_at timestamptz NULL
    """))
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.uzum_sync_log (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            started_at timestamptz NOT NULL,
            finished_at timestamptz NULL,
            status varchar(20) NOT NULL,
            error_message text NULL,
            upload_batch_id uuid NULL,
            trigger varchar(32) NOT NULL DEFAULT 'scheduled',
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_uzum_sync_log_started_at
        ON {SCHEMA}.uzum_sync_log (started_at DESC)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_uzum_sync_log_user_started
        ON {SCHEMA}.uzum_sync_log (user_id, started_at DESC)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_uzum_sync_log_user_started"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_uzum_sync_log_started_at"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.uzum_sync_log"))
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.users
        DROP COLUMN IF EXISTS last_api_sync_at
    """))
