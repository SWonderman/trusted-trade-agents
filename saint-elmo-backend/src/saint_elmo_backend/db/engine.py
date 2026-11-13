from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from saint_elmo_backend.core.settings import get_settings

# Importing registers the RLS after_begin listener on the Session class.
import saint_elmo_backend.db.tenancy  # noqa: F401


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()

    return create_async_engine(
        settings.app_db_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        # Discard connections the server closed while they sat in the pool
        pool_pre_ping=True,
        echo=settings.db_echo,
    )


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        get_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def dispose_engine() -> None:
    """
    Close pooled connections on shutdown. No-op if the engine was never created.
    """
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
