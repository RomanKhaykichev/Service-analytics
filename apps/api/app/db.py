from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator
from app.settings import get_settings

settings = get_settings()

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
