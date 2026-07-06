from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator
from app.settings import get_settings
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
settings = get_settings()

# Log database connection info when creating engine (without password)
def log_engine_db_info():
    """Log database connection info for engine creation without exposing password."""
    try:
        parsed = urlparse(settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://"))
        logger.info("=" * 60)
        logger.info("SQLAlchemy Engine Database Connection Info:")
        logger.info(f"  Host: {parsed.hostname or 'localhost'}")
        logger.info(f"  Port: {parsed.port or 5432}")
        logger.info(f"  Database: {parsed.path.lstrip('/') if parsed.path else 'N/A'}")
        logger.info(f"  User: {parsed.username or 'N/A'}")
        logger.info(f"  Schema: {settings.DB_SCHEMA}")
        logger.info(f"  Password: {'***' if parsed.password else 'N/A'}")
        logger.info("=" * 60)
    except Exception as e:
        logger.warning(f"Could not parse DATABASE_URL: {e}")

log_engine_db_info()

# Create database engine from DATABASE_URL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"connect_timeout": 10},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()


def qname(name: str) -> str:
    """
    Helper function to create qualified table/view name with schema.
    
    Args:
        name: Table or view name (without schema prefix)
        
    Returns:
        Qualified name in format: {schema}.{name}
    """
    return f"{settings.DB_SCHEMA}.{name}"


def ensure_fact_expenses_shop_columns() -> None:
    """Idempotent DDL for expenses shop filter (also in alembic 20260628_exp_shop)."""
    schema = settings.DB_SCHEMA
    try:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {schema}.stg_expenses ADD COLUMN IF NOT EXISTS shop_raw text"))
            conn.execute(text(f"ALTER TABLE {schema}.fact_expenses ADD COLUMN IF NOT EXISTS shop_raw text"))
            conn.execute(text(f"ALTER TABLE {schema}.fact_expenses ADD COLUMN IF NOT EXISTS shop_id uuid"))
        logger.info("fact_expenses shop columns ensured (shop_raw, shop_id)")
    except Exception as e:
        logger.warning("Could not ensure fact_expenses shop columns: %s", e)


def ensure_fact_leftout_fbs_qty_column() -> None:
    """Idempotent DDL for FBS stock (also in alembic 20260629_fbs_qty)."""
    schema = settings.DB_SCHEMA
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE {schema}.fact_leftout_old_snapshot "
                    "ADD COLUMN IF NOT EXISTS fbs_qty integer NOT NULL DEFAULT 0"
                )
            )
        logger.info("fact_leftout_old_snapshot.fbs_qty column ensured")
    except Exception as e:
        logger.warning("Could not ensure fact_leftout_old_snapshot.fbs_qty: %s", e)


def ensure_users_allowed_shops_column() -> None:
    """Idempotent DDL for shop allowlist override (also in alembic)."""
    schema = settings.DB_SCHEMA
    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"ALTER TABLE {schema}.users ADD COLUMN IF NOT EXISTS allowed_shops text")
            )
        logger.info("users.allowed_shops column ensured")
    except Exception as e:
        logger.warning("Could not ensure users.allowed_shops: %s", e)


def ensure_dim_shop_uzum_columns() -> None:
    """Idempotent DDL for Uzum shop metadata on dim_shop."""
    schema = settings.DB_SCHEMA
    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"ALTER TABLE {schema}.dim_shop ADD COLUMN IF NOT EXISTS uzum_shop_id INTEGER")
            )
            conn.execute(
                text(
                    f"ALTER TABLE {schema}.dim_shop "
                    "ADD COLUMN IF NOT EXISTS api_key_accessible BOOLEAN NOT NULL DEFAULT false"
                )
            )
        logger.info("dim_shop uzum columns ensured")
    except Exception as e:
        logger.warning("Could not ensure dim_shop uzum columns: %s", e)


def migrate_drop_trial_display_shop_column() -> None:
    """Перенос trial_display_shop → allowed_shops и удаление колонки (идемпотентно)."""
    import json

    schema = settings.DB_SCHEMA
    try:
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL lock_timeout = '5s'"))
            conn.execute(text("SET LOCAL statement_timeout = '30s'"))
            col = conn.execute(
                text(
                    """
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = :schema
                      AND table_name = 'users'
                      AND column_name = 'trial_display_shop'
                    """
                ),
                {"schema": schema},
            ).fetchone()
            if not col:
                return
            rows = conn.execute(
                text(
                    f"""
                    SELECT id::text, trial_display_shop
                    FROM {schema}.users
                    WHERE trial_display_shop IS NOT NULL
                      AND trim(trial_display_shop) <> ''
                      AND (
                          allowed_shops IS NULL
                          OR trim(allowed_shops) = ''
                          OR allowed_shops = '[]'
                      )
                    """
                )
            ).fetchall()
            for uid, shop in rows or []:
                if not shop:
                    continue
                payload = json.dumps([str(shop).strip()], ensure_ascii=False)
                conn.execute(
                    text(
                        f"UPDATE {schema}.users "
                        "SET allowed_shops = :p WHERE id = CAST(:uid AS uuid)"
                    ),
                    {"p": payload, "uid": uid},
                )
            conn.execute(
                text(f"ALTER TABLE {schema}.users DROP COLUMN IF EXISTS trial_display_shop")
            )
        logger.info("trial_display_shop migrated to allowed_shops and column dropped")
    except Exception as e:
        logger.warning("Could not migrate/drop users.trial_display_shop: %s", e)


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI.
    Yields a database session and ensures it's closed after use.
    On any exception, rolls back the transaction before closing.
    Sets search_path to app, public so unqualified table names resolve to the app schema.
    """
    db = SessionLocal()
    try:
        # Ensure unqualified names resolve to app schema first (insurance for any raw SQL)
        db.execute(text(f"SET search_path TO {settings.DB_SCHEMA}, public"))
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
