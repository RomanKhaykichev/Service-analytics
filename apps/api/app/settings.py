import os
from typing import Optional
from dotenv import load_dotenv

# Load .env file from apps/api directory
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)


class Settings:
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/service_analytics"
    )
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "app")
    
    # App environment
    APP_ENV: str = os.getenv("APP_ENV", "development")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Dev fallback for user_id (only used when APP_ENV=dev)
    DEFAULT_DEV_USER_ID: str = os.getenv(
        "DEFAULT_DEV_USER_ID",
        "00000000-0000-0000-0000-000000000001"
    )
    
    # JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production-secret-key-min-32-chars")
    JWT_ISSUER: str = os.getenv("JWT_ISSUER", "service-analytics-api")
    ACCESS_TTL_MIN: int = int(os.getenv("ACCESS_TTL_MIN", "15"))  # 15 minutes
    REFRESH_TTL_DAYS: int = int(os.getenv("REFRESH_TTL_DAYS", "30"))  # 30 days


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# Default settings instance for backward compatibility
settings = get_settings()
