from sqlalchemy import create_engine
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


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
