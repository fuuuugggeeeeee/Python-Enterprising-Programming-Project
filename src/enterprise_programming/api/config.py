"""Environment-driven application configuration."""

from typing import List, Literal, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration loaded from ``EPP_*`` environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="EPP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Enterprise Programming API"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite+pysqlite:///./enterprise.db"
    jwt_secret: str = "development-secret-change-before-production"
    jwt_issuer: str = "enterprise-programming-api"
    jwt_audience: str = "enterprise-programming-clients"
    access_token_minutes: int = Field(default=30, ge=1, le=1440)
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: Optional[str] = None
    allowed_origins: List[str] = Field(default_factory=list)
    rate_limit_per_minute: int = Field(default=120, ge=1, le=100_000)
    log_level: str = "INFO"
    json_logs: bool = True
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=32)

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.environment == "production":
            if len(self.jwt_secret) < 32 or self.jwt_secret.startswith(
                ("development-", "replace-")
            ):
                raise ValueError("EPP_JWT_SECRET must be a unique value of at least 32 characters")
            if not self.bootstrap_admin_password:
                raise ValueError("EPP_BOOTSTRAP_ADMIN_PASSWORD is required in production")
            if self.bootstrap_admin_password.startswith("replace-"):
                raise ValueError("EPP_BOOTSTRAP_ADMIN_PASSWORD must not be a placeholder")
        if self.bootstrap_admin_password and len(self.bootstrap_admin_password) < 12:
            raise ValueError("bootstrap admin password must be at least 12 characters")
        return self
