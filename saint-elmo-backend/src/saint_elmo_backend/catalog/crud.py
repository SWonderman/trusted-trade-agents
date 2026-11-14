from sqlalchemy import Select, cast, func, literal, null, or_, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from saint_elmo_backend.catalog.dtos import ProductMatch
from saint_elmo_backend.catalog.models import Product, ProductTranslation

# Each translation's search vector is built with its own language's configuration
_SEARCH_CONFIGS = ("pg_catalog.finnish", "pg_catalog.swedish", "pg_catalog.english")


def _text_query(query: str):
    """
    The query parsed once per language and ORed (`||`), so a single tsquery matches
    fi, sv and en translations at once and the search vector's GIN index applies.
    """
    tsqueries = [
        func.websearch_to_tsquery(cast(literal(config), REGCONFIG), query)
        for config in _SEARCH_CONFIGS
    ]
    combined = tsqueries[0]
    for tsquery in tsqueries[1:]:
        combined = combined.op("||")(tsquery)
    return combined


def _matching_product_ids(query: str) -> Select:
    """
    (product_id, relevance) for every product with a translation matching the query by
    full text, or by name trigram similarity (`%`, pg_trgm's threshold) to handle potential typos.
    Relevance is the better of the two scores and a product matching in several
    languages keeps its best one.
    """
    text_query = _text_query(query)
    return (
        select(
            ProductTranslation.product_id,
            func.max(
                func.greatest(
                    func.ts_rank(ProductTranslation.search_vector, text_query),
                    func.similarity(ProductTranslation.name, query),
                )
            ).label("relevance"),
        )
        .where(
            or_(
                ProductTranslation.search_vector.bool_op("@@")(text_query),
                ProductTranslation.name.bool_op("%")(query),
            )
        )
        .group_by(ProductTranslation.product_id)
    )


async def search_products(
    session: AsyncSession, *, query: str | None, limit: int, offset: int
) -> list[ProductMatch]:
    if query is None:
        stmt = select(Product, null().label("relevance")).order_by(
            Product.delivery_reliability.desc().nulls_last(), Product.code
        )
    else:
        matches = _matching_product_ids(query).subquery()
        stmt = (
            select(Product, matches.c.relevance)
            .join(matches, matches.c.product_id == Product.id)
            .order_by(matches.c.relevance.desc(), Product.code)
        )
    stmt = (
        stmt.limit(limit)
        .offset(offset)
        .options(
            selectinload(Product.translations),
            selectinload(Product.units),
            selectinload(Product.deposits),
            selectinload(Product.claims),
            selectinload(Product.diets),
            selectinload(Product.labels),
            joinedload(Product.category),
            joinedload(Product.vendor),
            joinedload(Product.brand),
        )
    )
    return [
        ProductMatch(product=product, relevance=relevance)
        for product, relevance in (await session.execute(stmt)).all()
    ]


async def count_products(session: AsyncSession, *, query: str | None) -> int:
    if query is None:
        stmt = select(func.count()).select_from(Product)
    else:
        stmt = select(func.count()).select_from(_matching_product_ids(query).subquery())
    return (await session.execute(stmt)).scalar_one()
