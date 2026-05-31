from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    web_url: str = Field(default="http://127.0.0.1:4412", alias="WEB_URL")
    api_url: str = Field(default="http://127.0.0.1:8617", alias="API_URL")

    postgres_host: str = Field(default="127.0.0.1", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=56432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="wozym", alias="POSTGRES_DB")
    postgres_user: str = Field(default="wozym", alias="POSTGRES_USER")
    postgres_password: str = Field(default="wozym", alias="POSTGRES_PASSWORD")
    database_url: str = Field(
        default="postgresql+psycopg://wozym:wozym@127.0.0.1:56432/wozym",
        alias="DATABASE_URL",
    )

    jwt_access_secret: str = Field(default="replace-local-access-secret", alias="JWT_ACCESS_SECRET")
    jwt_refresh_secret: str = Field(default="replace-local-refresh-secret", alias="JWT_REFRESH_SECRET")
    access_token_ttl_minutes: int = Field(default=15, alias="ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(default=30, alias="REFRESH_TOKEN_TTL_DAYS")

    smtp_host: str = Field(default="127.0.0.1", alias="SMTP_HOST")
    smtp_port: int = Field(default=11125, alias="SMTP_PORT")
    smtp_from: str = Field(default="no-reply@local.wozym", alias="SMTP_FROM")

    phone_verification_dev_mode: bool = Field(default=True, alias="PHONE_VERIFICATION_DEV_MODE")

    ai_card_assistant_enabled: bool = Field(default=False, alias="AI_CARD_ASSISTANT_ENABLED")
    ai_provider: str = Field(default="openai", alias="AI_PROVIDER")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    ai_text_model: str = Field(default="gpt-5.1", alias="AI_TEXT_MODEL")
    ai_vision_model: str = Field(default="gpt-5.1", alias="AI_VISION_MODEL")
    ai_fast_model: str = Field(default="gpt-5-mini", alias="AI_FAST_MODEL")
    ai_image_model: str = Field(default="gpt-image-1.5", alias="AI_IMAGE_MODEL")
    ai_timeout_seconds: int = Field(default=60, alias="AI_TIMEOUT_SECONDS")
    ai_max_images_per_draft: int = Field(default=5, alias="AI_MAX_IMAGES_PER_DRAFT")
    ai_enable_image_generation: bool = Field(default=False, alias="AI_ENABLE_IMAGE_GENERATION")


settings = Settings()

