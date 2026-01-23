from logging.config import fileConfig
from sqlalchemy import engine_from_config, text as sa_text
from sqlalchemy import pool
from alembic import context
import os
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.settings import get_settings
from app.db import Base

# Set up logger
logger = logging.getLogger("alembic.env")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from settings (same as API)
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Log database connection info for Alembic (without password)
def log_alembic_db_info():
    """Log database connection info for Alembic without exposing password."""
    try:
        parsed = urlparse(settings.DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://"))
        logger.info("=" * 60)
        logger.info("Alembic Database Connection Info:")
        logger.info(f"  Host: {parsed.hostname or 'localhost'}")
        logger.info(f"  Port: {parsed.port or 5432}")
        logger.info(f"  Database: {parsed.path.lstrip('/') if parsed.path else 'N/A'}")
        logger.info(f"  User: {parsed.username or 'N/A'}")
        logger.info(f"  Schema: {settings.DB_SCHEMA}")
        logger.info(f"  Password: {'***' if parsed.password else 'N/A'}")
        logger.info("=" * 60)
    except Exception as e:
        logger.warning(f"Could not parse DATABASE_URL: {e}")

log_alembic_db_info()

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=settings.DB_SCHEMA,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Set schema for operations
        connection.execute(sa_text(f"SET search_path TO {settings.DB_SCHEMA}, public"))
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=settings.DB_SCHEMA,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
