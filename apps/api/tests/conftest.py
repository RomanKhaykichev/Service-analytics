"""
Ensure DB columns/tables used by tests exist (idempotent; mirrors migration 20260155).
"""
import pytest
from sqlalchemy import text

from app.db import engine
from app.settings import get_settings


def _db_ok() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def ensure_phone_verification_schema():
    if not _db_ok():
        return
    s = get_settings()
    schema = s.DB_SCHEMA
    with engine.begin() as conn:
        conn.execute(
            text(
                f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS phone_verified_at timestamptz"
            )
        )
        conn.execute(
            text(f"""
                CREATE TABLE IF NOT EXISTS {schema}.otp_attempts (
                    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id uuid REFERENCES {schema}.users(id) ON DELETE CASCADE,
                    phone_normalized varchar(64) NOT NULL,
                    kind varchar(32) NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
            """)
        )
        conn.execute(
            text(f"""
                CREATE INDEX IF NOT EXISTS ix_otp_attempts_phone_created
                ON {schema}.otp_attempts (phone_normalized, created_at DESC)
            """)
        )
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {schema}.pending_registrations (
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
        conn.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS ix_pending_registrations_phone
                ON {schema}.pending_registrations (phone)
                """
            )
        )
        conn.execute(
            text(
                f"""
                ALTER TABLE {schema}.verification_codes
                ADD COLUMN IF NOT EXISTS pending_id uuid NULL
                """
            )
        )
