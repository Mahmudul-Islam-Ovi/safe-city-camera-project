"""Shared pytest fixtures for the AI engine."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.config.settings import get_settings


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear the settings cache around each test so env overrides never leak between tests."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
