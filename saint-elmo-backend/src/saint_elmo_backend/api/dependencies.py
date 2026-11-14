from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.db.engine import get_sessionmaker


async def get_session() -> AsyncGenerator[AsyncSession]:
    session_factory = get_sessionmaker()

    async with session_factory() as session:
        yield session
