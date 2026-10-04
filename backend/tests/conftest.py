"""Shared pytest fixtures for the backend."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.config.settings import get_settings


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("ENVIRONMENT", "test")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
