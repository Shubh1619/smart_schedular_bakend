from __future__ import annotations

import json
from typing import Any, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Smart Schedular API"
    database_url: str = Field(alias="DATABASE_URL")
    frontend_base_url: str = Field(default="https://smart-schedular.mrshubh2007.workers.dev", alias="FRONTEND_BASE_URL")
    auto_create_tables: bool = Field(default=True, alias="AUTO_CREATE_TABLES")

    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    otp_expire_minutes: int = Field(alias="OTP_EXPIRE_MINUTES")

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173", "https://smart-schedular.mrshubh2007.workers.dev"],
        alias="CORS_ORIGINS",
    )
    cors_origin_regex: Optional[str] = Field(
        default=r"^https://([a-z0-9-]+\.)*workers\.dev$",
        alias="CORS_ORIGIN_REGEX",
    )

    smtp_host: Optional[str] = Field(default=None, alias="MAIL_SERVER")
    smtp_port: int = Field(default=587, alias="MAIL_PORT")
    smtp_user: Optional[str] = Field(default=None, alias="MAIL_USERNAME")
    smtp_password: Optional[str] = Field(default=None, alias="MAIL_PASSWORD")
    smtp_from: str = Field(default="noreply@smartschedular.local", alias="MAIL_FROM")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


settings = Settings()
