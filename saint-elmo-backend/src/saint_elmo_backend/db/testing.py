"""
Database helpers for the integration test suite.

Tests run against a separate `<name>_test` database so they can truncate freely
without touching the seeded dev catalog. Every destructive helper refuses to run
against a database whose name does not end in `_test`.
"""

from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DATABASE_SUFFIX = "_test"


class NotATestDatabase(Exception):
    """Refused to modify a database that is not a `_test` database."""


def to_test_database_url(url: str) -> str:
    """
    Same server and credentials, database name suffixed with `_test`.
    """
    parsed = make_url(url)
    database = parsed.database or ""
    if not database.endswith(TEST_DATABASE_SUFFIX):
        database += TEST_DATABASE_SUFFIX
    return parsed.set(database=database).render_as_string(hide_password=False)


def _ensure_test_database(url: str) -> None:
    database = make_url(url).database or ""
    if not database.endswith(TEST_DATABASE_SUFFIX):
        raise NotATestDatabase(database)


async def create_database(url: str) -> None:
    """
    Create the test database if it does not exist yet. Needs CREATEDB.
    """
    _ensure_test_database(url)

    parsed = make_url(url)
    # CREATE DATABASE cannot run inside a transaction, nor in the target database
    engine = create_async_engine(
        parsed.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": parsed.database},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{parsed.database}"'))
    finally:
        await engine.dispose()


async def truncate_all(url: str) -> None:
    """
    Empty every table except alembic_version. Needs the owner role.
    """
    _ensure_test_database(url)

    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            tables = (
                await conn.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public' "
                        "AND tablename <> 'alembic_version'"
                    )
                )
            ).scalars().all()
            if tables:
                names = ", ".join(f'"{name}"' for name in tables)
                await conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    finally:
        await engine.dispose()
