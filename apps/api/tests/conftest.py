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


@pytest.fixture(scope="session")
def ensure_dim_shop_and_fact_sales_for_tests():
    """
    Optional: only for tests that need GET /api/shops against dim_shop + fact_sales.

    GET /api/shops uses a UNION over dim_shop and fact_sales; both relations must exist
    or the handler falls back to v_sales_daily and ignores dim_shop-only rows.
    Idempotent DDL aligned with scripts/ensure_import_tables.py (minimal).

    Not autouse — request it explicitly on tests that require this schema.
    """
    if not _db_ok():
        return
    s = get_settings()
    schema = s.DB_SCHEMA
    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {schema}.dim_shop (
                    shop_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id uuid NOT NULL,
                    shop_name text NOT NULL,
                    UNIQUE (user_id, shop_name)
                )
                """
            )
        )
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_dim_shop_user_id ON {schema}.dim_shop (user_id)"
            )
        )
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {schema}.fact_sales (
                    user_id uuid NOT NULL,
                    upload_batch_id uuid NOT NULL,
                    shop_id uuid,
                    status text,
                    date_created timestamptz,
                    date_received timestamptz,
                    order_no text,
                    sku text,
                    barcode text,
                    product_name text,
                    category text,
                    barcode_norm text,
                    qty int DEFAULT 0,
                    returns_qty int DEFAULT 0,
                    revenue_sum numeric(18,2) DEFAULT 0,
                    revenue_net_sum numeric(18,2) DEFAULT 0,
                    commission_sum numeric(18,2) DEFAULT 0,
                    logistics_sum numeric(18,2) DEFAULT 0,
                    price_sum numeric(18,2) DEFAULT 0,
                    promo_sum numeric(18,2) DEFAULT 0,
                    cogs_sum numeric(18,2) DEFAULT 0,
                    UNIQUE (user_id, order_no, barcode, date_created)
                )
                """
            )
        )
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS ix_fact_sales_user_batch ON {schema}.fact_sales (user_id, upload_batch_id)"
            )
        )
