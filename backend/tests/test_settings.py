"""Phase 1 tests: backend configuration."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config.settings import PROJECT_ROOT, Settings


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)  # type: ignore[call-arg]


def test_defaults() -> None:
    s = make()
    assert s.service_name == "backend"
    assert s.api_prefix == "/api"
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert s.auth_enabled is False


def test_cors_origins_parsed_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000/, https://soc.example.org")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.cors_origins == ["http://localhost:3000", "https://soc.example.org"]


def test_invalid_cors_origin_rejected() -> None:
    with pytest.raises(ValidationError, match="Invalid CORS origin"):
        make(cors_origins="localhost:3000")


@pytest.mark.parametrize(("raw", "expected"), [("api", "/api"), ("/api/", "/api"), ("/", "")])
def test_api_prefix_normalised(raw: str, expected: str) -> None:
    assert make(api_prefix=raw).api_prefix == expected


def test_production_rejects_default_secrets() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make(environment="production")


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="Wildcard"):
        make(
            environment="production",
            secret_key="x" * 40,
            internal_api_key="y" * 30,
            cors_origins="*",
        )


def test_production_accepts_strong_config() -> None:
    s = make(
        environment="production",
        secret_key="x" * 40,
        internal_api_key="y" * 30,
        cors_origins="https://soc.example.org",
    )
    assert s.environment == "production"


def test_evidence_path_resolves_against_root() -> None:
    assert make(evidence_dir="evidence").evidence_path == (PROJECT_ROOT / "evidence").resolve()


def test_env_example_loads() -> None:
    s = Settings(_env_file=PROJECT_ROOT / ".env.example")  # type: ignore[call-arg]
    assert s.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]
    assert s.rate_limit_per_minute == 120
