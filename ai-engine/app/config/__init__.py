"""Configuration package. Import ``get_settings()`` everywhere instead of reading env vars directly."""

from app.config.settings import AI_ENGINE_DIR, PROJECT_ROOT, Settings, get_settings

__all__ = ["AI_ENGINE_DIR", "PROJECT_ROOT", "Settings", "get_settings"]
