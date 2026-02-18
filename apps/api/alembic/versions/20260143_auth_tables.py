"""create auth tables (users, auth_identities, refresh_tokens, verification_codes)

Revision ID: 20260143_auth_tables
Revises: 20260143_add_name_to_manual_expenses
Create Date: 2026-01-43 00:00:00.000000

Creates app.users, app.auth_identities, app.refresh_tokens, app.verification_codes
for registration/login and profile (GET/PATCH /api/auth/me).
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "20260143_auth_tables"
down_revision: Union[str, None] = "20260143_add_name_to_manual_expenses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "app"


def upgrade() -> None:
    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email varchar(255) UNIQUE,
            full_name varchar(255),
            phone varchar(50) UNIQUE,
            is_active boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_users_email ON {SCHEMA}.users (email)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_users_phone ON {SCHEMA}.users (phone)
    """))

    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.auth_identities (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            provider varchar(50) NOT NULL,
            identifier varchar(255) NOT NULL,
            password_hash varchar(255),
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_auth_identities_user_id ON {SCHEMA}.auth_identities (user_id)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_auth_identities_identifier ON {SCHEMA}.auth_identities (identifier)
    """))

    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.refresh_tokens (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid NOT NULL REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            token_hash varchar(255) NOT NULL UNIQUE,
            revoked_at timestamptz,
            expires_at timestamptz NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON {SCHEMA}.refresh_tokens (user_id)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON {SCHEMA}.refresh_tokens (token_hash)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_refresh_tokens_expires_at ON {SCHEMA}.refresh_tokens (expires_at)
    """))

    op.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA}.verification_codes (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id uuid REFERENCES {SCHEMA}.users(id) ON DELETE CASCADE,
            channel varchar(50) NOT NULL,
            destination varchar(255) NOT NULL,
            code_hash varchar(255) NOT NULL,
            expires_at timestamptz NOT NULL,
            consumed_at timestamptz,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_verification_codes_user_id ON {SCHEMA}.verification_codes (user_id)
    """))
    op.execute(text(f"""
        CREATE INDEX IF NOT EXISTS ix_verification_codes_expires_at ON {SCHEMA}.verification_codes (expires_at)
    """))


def downgrade() -> None:
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.verification_codes"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.refresh_tokens"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.auth_identities"))
    op.execute(text(f"DROP TABLE IF EXISTS {SCHEMA}.users"))
