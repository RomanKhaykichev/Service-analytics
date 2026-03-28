import os
from typing import Optional
from dotenv import load_dotenv

# Load .env.example first (defaults), then .env (overrides). If .env is missing, only .env.example is used.
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
load_dotenv(env_example_path)
load_dotenv(env_path)


class Settings:
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/service_analytics"
    )
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "app")
    
    # App environment (dev/prod, default: dev)
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    # Optional override (e.g. CI); if set to "prod", same restrictions as APP_ENV=prod
    ENV: str = os.getenv("ENV", "")
    
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
    PENDING_TTL_HOURS: int = int(os.getenv("PENDING_TTL_HOURS", "24"))

    # Admin: comma-separated list of emails or UUIDs allowed to access /api/admin/*
    ADMIN_USER_IDS: str = os.getenv("ADMIN_USER_IDS", "")

    # SMS (Eskiz) — https://notify.eskiz.uz/api
    ESKIZ_BASE_URL: str = os.getenv("ESKIZ_BASE_URL", "https://notify.eskiz.uz/api").rstrip("/")
    ESKIZ_EMAIL: str = os.getenv("ESKIZ_EMAIL", "")
    ESKIZ_PASSWORD: str = os.getenv("ESKIZ_PASSWORD", "")
    ESKIZ_FROM: str = os.getenv("ESKIZ_FROM", "")
    SMS_DEBUG_LOG_CODE: bool = os.getenv("SMS_DEBUG_LOG_CODE", "false").lower() in ("1", "true", "yes")

    # OTP for phone verification (sha256(OTP_SECRET + code))
    OTP_SECRET: str = os.getenv("OTP_SECRET", "change-me-otp-secret-min-16-chars")


_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# Default settings instance for backward compatibility
settings = get_settings()
