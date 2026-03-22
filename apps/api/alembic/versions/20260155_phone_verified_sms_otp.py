"""users.phone_verified_at and otp_attempts for SMS verification

Revision ID: 20260155
Revises: 20260154
Create Date: 2026-01-55 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260155"
down_revision: Union[str, None] = "20260154"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        ALTER TABLE {SCHEMA}.users
        ADD COLUMN IF NOT EXISTS phone_verified_at timestamptz
    """))
    # Existing accounts with a phone number: treat as verified (SMS flow is new).
    op.execute(text(f"""
        UPDATE {SCHEMA}.users
        SET phone_verified_at = now()
        WHERE phone_verified_at IS NULL
          AND phone IS NOT NULL
          AND trim(phone) <> ''
    """))
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.otp_attempts (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            phone_normalized varchar(64) NOT NULL,
            kind varchar(32) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_otp_attempts_phone_created
        ON {SCHEMA}.otp_attempts (phone_normalized, created_at DESC)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.otp_attempts"))
    op.execute(text(f"ALTER TABLE {SCHEMA}.users DROP COLUMN IF EXISTS phone_verified_at"))
