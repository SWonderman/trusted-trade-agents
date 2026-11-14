from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from saint_elmo_backend.catalog.models import Product


async def search_product_ids(
    session: AsyncSession, *, limit: int, offset: int
) -> list[int]:
    stmt = (
        select(Product.id)
        .order_by(Product.delivery_reliability.desc().nulls_last(), Product.code)
        .limit(limit)
        .offset(offset)
    )
    return list((await session.execute(stmt)).scalars().all())


async def count_products(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Product)
    return (await session.execute(stmt)).scalar_one()


async def load_products(session: AsyncSession, product_ids: Sequence[int]) -> list[Product]:
    stmt = (
        select(Product)
        .where(Product.id.in_(product_ids))
        .options(selectinload(Product.translations))
    )
    return list((await session.execute(stmt)).scalars().all())
