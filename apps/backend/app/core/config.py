import os
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/smart_academic_ai",
        description="SQLAlchemy Async Database URL"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis Connection URL"
    )

    # JWT Authentication
    JWT_SECRET: str = Field(
        default="dev-secret-key-smart-academic-ai-32-chars-minimum",
        description="Secret key for signing JWT tokens"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @field_validator("JWT_SECRET")

    def validate_jwt_secret(cls, v: str, info) -> str:
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production" and (len(v) < 32 or "dev-secret" in v):
            raise ValueError("JWT_SECRET must be at least 32 characters long and secure in production.")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
