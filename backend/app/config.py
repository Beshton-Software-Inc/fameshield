"""
Application configuration management.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "FameShield"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = Field(..., min_length=32)

    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str
    celery_broker_url: str
    celery_result_backend: str

    # AWS
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    aws_s3_bucket: str
    aws_s3_evidence_prefix: str = "evidence/"

    # Anthropic Claude API
    anthropic_api_key: str
    claude_model: str = "claude-3-5-sonnet-20241022"
    claude_max_tokens: int = 4096

    # Social Media APIs
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_bearer_token: Optional[str] = None

    instagram_app_id: Optional[str] = None
    instagram_app_secret: Optional[str] = None

    tiktok_client_key: Optional[str] = None
    tiktok_client_secret: Optional[str] = None

    youtube_api_key: Optional[str] = None

    # JWT Authentication
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # Email
    email_provider: str = "sendgrid"
    sendgrid_api_key: Optional[str] = None
    from_email: str = "noreply@fameshield.com"

    # SMS
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_phone: Optional[str] = None

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # Monitoring
    monitoring_interval_minutes: int = 15
    max_content_items_per_poll: int = 100

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
