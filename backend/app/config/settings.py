"""Validated configuration for the backend service.

Reads, in increasing priority: defaults → ``<project-root>/.env`` → ``backend/.env`` →
real environment variables. Field names map to upper-case env vars.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR: Path = Path(__file__).resolve().parents[2]
PROJECT_ROOT: Path = Path(os.getenv("SAFE_CITY_ROOT", str(BACKEND_DIR.parent))).resolve()

_INSECURE_SECRETS = {"dev-only-insecure-secret-change-me", "changeme", "secret", ""}
_INSECURE_INTERNAL_KEYS = {"dev-only-internal-key-change-me", "changeme", ""}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---------- General ----------
    service_name: str = "backend"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["console", "json"] = "console"

    # ---------- HTTP ----------
    backend_host: str = "0.0.0.0"
    backend_port: int = Field(8000, ge=1, le=65535)
    api_prefix: str = "/api"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    # ---------- Data stores ----------
    database_url: str = "postgresql+asyncpg://safecity:change_me_dev_only@localhost:5432/safecity"
    redis_url: str = "redis://localhost:6379/0"

    # ---------- Security ----------
    secret_key: str = "dev-only-insecure-secret-change-me"
    access_token_expire_minutes: int = Field(60, ge=5, le=24 * 60)
    internal_api_key: str = "dev-only-internal-key-change-me"
    auth_enabled: bool = False
    rate_limit_per_minute: int = Field(120, ge=1)
    ws_max_connections: int = Field(50, ge=1, le=10_000)

    # ---------- Integration ----------
    ai_engine_url: str = "http://localhost:8001"
    evidence_dir: Path = Path("evidence")
    evidence_retention_days: int = Field(30, ge=1)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: object) -> list[str]:
        if isinstance(value, str):
            origins = [v.strip().rstrip("/") for v in value.split(",") if v.strip()]
        elif isinstance(value, (list, tuple)):
            origins = [str(v).strip().rstrip("/") for v in value if str(v).strip()]
        else:
            raise ValueError("CORS_ORIGINS must be a comma-separated string or list")
        for origin in origins:
            if origin != "*" and not origin.startswith(("http://", "https://")):
                raise ValueError(f"Invalid CORS origin: {origin!r}")
        return origins

    @field_validator("api_prefix")
    @classmethod
    def _normalise_prefix(cls, value: str) -> str:
        value = "/" + value.strip().strip("/")
        return "" if value == "/" else value

    @model_validator(mode="after")
    def _production_hardening(self) -> Settings:
        """Refuse to start in production with development secrets or wildcard CORS."""
        if self.environment == "production":
            if self.secret_key in _INSECURE_SECRETS or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be set to a random value of >= 32 chars in production")
            if self.internal_api_key in _INSECURE_INTERNAL_KEYS or len(self.internal_api_key) < 24:
                raise ValueError("INTERNAL_API_KEY must be set to a random value of >= 24 chars in production")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS_ORIGINS is not allowed in production")
        return self

    @property
    def evidence_path(self) -> Path:
        return self.evidence_dir if self.evidence_dir.is_absolute() else (PROJECT_ROOT / self.evidence_dir).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
