"""
LeadForge AI - Configuration Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "LeadForge AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql://leadforge:leadforge_password@localhost:5432/leadforge"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]

    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    NEVERBOUNCE_API_KEY: Optional[str] = None

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None

    # Scraping
    PROXY_ROTATION_ENABLED: bool = True
    PROXY_SERVICE_URL: Optional[str] = None
    PROXY_SERVICE_USERNAME: Optional[str] = None
    PROXY_SERVICE_PASSWORD: Optional[str] = None
    SCRAPER_CONCURRENT_REQUESTS: int = 5
    SCRAPER_DELAY_MIN: int = 1
    SCRAPER_DELAY_MAX: int = 3
    SCRAPER_MAX_RETRIES: int = 3

    # Stripe (Future)
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Monitoring (Optional)
    SENTRY_DSN: Optional[str] = None
    POSTHOG_KEY: Optional[str] = None
    POSTHOG_HOST: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
