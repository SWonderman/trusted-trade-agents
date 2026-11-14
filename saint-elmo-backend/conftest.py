"""
Shared pytest fixtures.

Lives at the project root so it is visible to every co-located domain test
(e.g. catalog/tests/). Integration-oriented: the DB fixtures need the compose
Postgres running, but run against a separate `<POSTGRES_DB>_test` database that is
created and migrated on first use, so the seeded dev catalog is never touched.
Pure unit tests request none of these fixtures and stay DB-free.
"""

import base64
import os
import secrets

# NOTE(sw): keys do not depend on the developer's .env keys
os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
# A demo setting in a developer's .env must not change what tests expect of closing times
os.environ["OFFERS_IGNORE_CLOSING_TIME"] = "false"
os.environ["AGENT_TOKEN_SIGNING_KEY"] = base64.urlsafe_b64encode(os.urandom(32)).decode()

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command
from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.db.engine import dispose_engine, get_engine, get_sessionmaker
from saint_elmo_backend.db.seeders.code_lists import seed_code_lists
from saint_elmo_backend.db.testing import create_database, to_test_database_url, truncate_all
from saint_elmo_backend.main import create_app

ALEMBIC_INI = Path(__file__).parent / "alembic.ini"


@pytest.fixture(scope="session")
def test_db_url() -> Iterator[str]:
    """
    Point every settings consumer (app, Alembic, seeders) at the test database,
    then create and migrate it.
    """
    url = to_test_database_url(get_settings().db_url)

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DB_URL", url)
        get_settings.cache_clear()

        asyncio.run(create_database(url))
        command.upgrade(Config(ALEMBIC_INI), "head")

        yield url

    get_settings.cache_clear()


@pytest.fixture(scope="session")
def app(test_db_url) -> FastAPI:
    return create_app()


@pytest.fixture
async def clean_db(test_db_url) -> None:
    """
    Start from an empty test DB (except alembic_version). Opt-in, not autouse.
    """
    await truncate_all(test_db_url)


@pytest.fixture
async def reference_data(clean_db, session) -> None:
    """
    GS1 code lists only; tests insert the products they need via the factories.
    """
    await seed_code_lists(session=session)
    await session.commit()


@pytest.fixture
async def session(test_db_url) -> AsyncIterator[AsyncSession]:
    """
    Session on the test DB, for arranging data and checking results.
    """
    engine = create_async_engine(test_db_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            yield session
    finally:
        await engine.dispose()


@pytest.fixture
async def client(app, clean_db) -> AsyncIterator[AsyncClient]:
    # The cached engine is bound to the event loop that created it, and every test
    # runs on its own loop: rebuild it for this test and dispose it afterwards.
    get_sessionmaker.cache_clear()
    get_engine.cache_clear()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client
    finally:
        await dispose_engine()
        get_sessionmaker.cache_clear()
        get_engine.cache_clear()
