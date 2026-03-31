"""pending registrations and verification pending link

Revision ID: 20260156
Revises: 20260155
Create Date: 2026-03-23 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260156"
down_revision: Union[str, None] = "20260155"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {SCHEMA}.pending_registrations (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                email text UNIQUE NOT NULL,
                full_name text NULL,
                phone text NOT NULL,
                password_hash text NOT NULL,
                consent_processing boolean NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                expires_at timestamptz NOT NULL,
                attempts int NOT NULL DEFAULT 0
            )
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_pending_registrations_phone
            ON {SCHEMA}.pending_registrations (phone)
            """
        )
    )
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.verification_codes
            ADD COLUMN IF NOT EXISTS pending_id uuid NULL
            """
        )
    )
    # Backward-compatible cleanup: if verification_codes already contains
    # pending_id values that do not exist in pending_registrations,
    # null them before adding FK to avoid upgrade failure on existing DBs.
    op.execute(
        text(
            f"""
            UPDATE {SCHEMA}.verification_codes vc
            SET pending_id = NULL
            WHERE pending_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM {SCHEMA}.pending_registrations pr
                WHERE pr.id = vc.pending_id
              )
            """
        )
    )
    op.execute(
        text(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_constraint
                    WHERE conname = 'fk_verification_codes_pending_id'
                ) THEN
                    ALTER TABLE {SCHEMA}.verification_codes
                    ADD CONSTRAINT fk_verification_codes_pending_id
                    FOREIGN KEY (pending_id)
                    REFERENCES {SCHEMA}.pending_registrations (id)
                    ON DELETE CASCADE;
                END IF;
            END $$;
            """
        )
    )
    op.execute(
        text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_verification_codes_pending_id
            ON {SCHEMA}.verification_codes (pending_id)
            """
        )
    )


def downgrade() -> None:
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_verification_codes_pending_id"))
    op.execute(
        text(
            f"""
            ALTER TABLE {SCHEMA}.verification_codes
            DROP CONSTRAINT IF EXISTS fk_verification_codes_pending_id
            """
        )
    )
    op.execute(text(f"ALTER TABLE {SCHEMA}.verification_codes DROP COLUMN IF EXISTS pending_id"))
    op.execute(text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_pending_registrations_phone"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.pending_registrations"))
