"""admin: upload_batch created_at/updated_at; users admin_notes, trial_ends_at, plan

Revision ID: 20260147_admin
Revises: 20260146_merge_heads
Create Date: 2026-01-47 00:00:00.000000

Adds:
- app.upload_batch: created_at, updated_at (for admin import metrics)
- app.users: admin_notes (text), trial_ends_at (timestamptz), plan (varchar default 'trial')
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260147_admin"
down_revision: Union[str, None] = "20260146_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.upload_batch
        ADD COLUMN IF NOT EXISTS created_at timestamptz NOT NULL DEFAULT now()
    """))
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.upload_batch
        ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now()
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_upload_batch_created_at ON {SCHEMA}.upload_batch (created_at)
    """))
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.users
        ADD COLUMN IF NOT EXISTS admin_notes text
    """))
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.users
        ADD COLUMN IF NOT EXISTS trial_ends_at timestamptz
    """))
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.users
        ADD COLUMN IF NOT EXISTS plan varchar(50) NOT NULL DEFAULT 'trial'
    """))


def downgrade() -> None:
    op.execute(text(f"ALTER TABLE {SCHEMA}.upload_batch DROP COLUMN IF EXISTS updated_at"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.upload_batch DROP COLUMN IF EXISTS created_at"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_upload_batch_created_at"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN IF EXISTS admin_notes"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN IF EXISTS trial_ends_at"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN IF EXISTS plan"))
