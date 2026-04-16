import os
from typing import List, Optional
from dotenv import load_dotenv

# .env.example first, then .env; override=True so real .env wins (dotenv default would not override keys already set).
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
env_example_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
load_dotenv(env_example_path)
load_dotenv(env_path, override=True)


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
    # Текст SMS с OTP: должен совпадать с шаблоном, согласованным в Eskiz (название ресурса + цель + {code}).
    SMS_OTP_TEMPLATE: str = os.getenv(
        "SMS_OTP_TEMPLATE",
        "Kod dlya registratsii i podtverzhdeniya nomera na sayte profiboard.uz (PROFiboard): {code}",
    )

    # OTP for phone verification (sha256(OTP_SECRET + code))
    OTP_SECRET: str = os.getenv("OTP_SECRET", "change-me-otp-secret-min-16-chars")

    # Cross-subdomain refresh cookie (e.g. .profiboard.uz for api.* + app.*). Only used when prod cookie mode.
    COOKIE_DOMAIN: str = os.getenv("COOKIE_DOMAIN", "").strip()

    def is_prod(self) -> bool:
        v = (self.ENV or self.APP_ENV or "").strip().lower()
        return v == "prod"

    def validate_for_environment(self) -> None:
        """
        Fail-fast validation for production.
        Prevents starting the service with placeholder secrets.
        """
        if not self.is_prod():
            return

        placeholder_markers = ("change-me", "i_like_to_play_computer")
        jwt = (self.JWT_SECRET or "").strip()
        otp = (self.OTP_SECRET or "").strip()

        if not jwt or len(jwt) < 32 or any(m in jwt.lower() for m in placeholder_markers):
            raise RuntimeError(
                "Invalid JWT_SECRET for production. "
                "Set a strong random secret (min 32 chars) via environment variables."
            )

        if not otp or len(otp) < 16 or any(m in otp.lower() for m in placeholder_markers):
            raise RuntimeError(
                "Invalid OTP_SECRET for production. "
                "Set a strong random secret (min 16 chars) via environment variables."
            )


_settings_instance: Optional[Settings] = None


def _default_cors_origins() -> List[str]:
    return [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://profiboard.uz",
        "https://www.profiboard.uz",
        "https://app.profiboard.uz",
    ]


def get_cors_origins() -> List[str]:
    """
    Comma-separated CORS_ORIGINS; if unset, default list (localhost + profiboard).
    Production: set e.g. CORS_ORIGINS=https://app.profiboard.uz,https://profiboard.uz
    """
    raw = (os.getenv("CORS_ORIGINS") or "").strip()
    if not raw:
        return _default_cors_origins()
    return [x.strip() for x in raw.split(",") if x.strip()]


def get_settings() -> Settings:
    """Get settings singleton instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
        _settings_instance.validate_for_environment()
    return _settings_instance


# Default settings instance for backward compatibility
settings = get_settings()
