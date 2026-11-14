from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.db.engine import get_sessionmaker
from saint_elmo_backend.valio_aimo.client import ValioAimoClient


async def get_session() -> AsyncGenerator[AsyncSession]:
    session_factory = get_sessionmaker()

    async with session_factory() as session:
        yield session


def get_valio_aimo_client(request: Request) -> ValioAimoClient:
    """
    The client `lifespan` created. Tests override this with `valio_aimo.testing`.
    """
    return request.app.state.valio_aimo_client
