from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from saint_elmo_backend.catalog.models import Product


async def search_products(
    session: AsyncSession, *, limit: int, offset: int
) -> list[Product]:
    stmt = (
        select(Product)
        .order_by(Product.delivery_reliability.desc().nulls_last(), Product.code)
        .limit(limit)
        .offset(offset)
        .options(selectinload(Product.translations))
    )
    return list((await session.execute(stmt)).scalars().all())


async def count_products(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Product)
    return (await session.execute(stmt)).scalar_one()
