"""Database engine, async session factory, and Base model for Safe City AI.

Supports:
- PostgreSQL + asyncpg (Docker or production)
- Automatic fallback to local SQLite (safecity.db) if PostgreSQL credentials fail or host is down
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import PROJECT_ROOT, get_settings
from app.core.logger import get_logger

log = get_logger(__name__)

settings = get_settings()


def _create_engine_and_session(
    url: str,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    connect_args = (
        {"check_same_thread": False} if "sqlite" in url.lower() else {"timeout": 3}
    )
    eng = create_async_engine(
        url,
        echo=False,
        future=True,
        connect_args=connect_args,
    )
    session_factory = async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return eng, session_factory


engine, AsyncSessionLocal = _create_engine_and_session(settings.database_url)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create tables if they don't exist. Falls back to SQLite if PostgreSQL fails."""
    global engine, AsyncSessionLocal
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("Database tables initialized successfully on %s", engine.url.drivername)
    except Exception as exc:
        if "sqlite" not in settings.database_url.lower():
            sqlite_path = (PROJECT_ROOT / "backend" / "safecity.db").resolve()
            sqlite_url = f"sqlite+aiosqlite:///{sqlite_path}"
            log.warning(
                "Primary database (%s) connection failed: %s. Falling back to local SQLite: %s",
                engine.url.drivername,
                exc,
                sqlite_url,
            )
            await engine.dispose()
            engine, AsyncSessionLocal = _create_engine_and_session(sqlite_url)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            log.info("SQLite database tables initialized successfully at %s", sqlite_path)
        else:
            raise
