import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.db.seeders.catalog import seed_catalog
from saint_elmo_backend.db.seeders.code_lists import seed_code_lists
from saint_elmo_backend.db.seeders.demo import seed_demo


async def run_seeders() -> None:
    settings = get_settings()

    engine = create_async_engine(settings.db_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with maker() as session:
            try:
                # Code lists first: catalogue rows reference them. The demo buyers
                # last: their mandates name catalogue codes
                await seed_code_lists(session=session)
                await seed_catalog(session=session, data_dir=settings.catalog_data_dir)
                await seed_demo(session=session)
                await session.commit()
            except Exception as e:
                logger.error(f"Error while seeding: {e}")
                await session.rollback()
                raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_seeders())
