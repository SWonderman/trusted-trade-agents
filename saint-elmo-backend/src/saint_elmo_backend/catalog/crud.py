from collections.abc import Collection
from typing import Any

from sqlalchemy import ColumnElement, Select, and_, case, cast, func, literal, null, or_, select
from sqlalchemy.dialects.postgresql import REGCONFIG
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, joinedload, selectinload

from saint_elmo_backend.catalog.dtos import ProductFilters, ProductMatch
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.catalog.models import (
    Category,
    Product,
    ProductClaim,
    ProductDiet,
    ProductLabel,
    ProductTranslation,
    Vendor,
)

# Each translation's search vector is built with its own language's configuration
_SEARCH_CONFIGS: dict[Language, str] = {
    Language.FI: "pg_catalog.finnish",
    Language.SV: "pg_catalog.swedish",
    Language.EN: "pg_catalog.english",
}

# ts_rank normalization flag: rank / (rank + 1), which keeps the rank in [0, 1)
_RANK_IN_UNIT_RANGE = 32


def _text_query(query: str) -> ColumnElement[Any]:
    """
    The query parsed once per language and ORed (`||`), so a single tsquery matches
    fi, sv and en translations at once and the search vector's GIN index applies.
    """
    tsqueries = [
        func.websearch_to_tsquery(cast(literal(config), REGCONFIG), query)
        for config in _SEARCH_CONFIGS.values()
    ]
    combined = tsqueries[0]
    for tsquery in tsqueries[1:]:
        combined = combined.op("||")(tsquery)
    return combined


def _matching_product_ids(query: str) -> Select:
    """
    (product_id, relevance) for every product with a translation matching the query by
    full text, or by name trigram similarity (`%`, pg_trgm's threshold) to handle potential typos.

    Trigram similarity is only the fallback: full-text matches score in [0.5, 1) and
    fuzzy-only matches in [0, 0.5], so every full-text match ranks above every fuzzy
    one. A product matching in several languages keeps its best score.
    """
    text_query = _text_query(query)
    text_match = ProductTranslation.search_vector.bool_op("@@")(text_query)
    relevance = case(
        (
            text_match,
            0.5
            + func.ts_rank(ProductTranslation.search_vector, text_query, _RANK_IN_UNIT_RANGE) / 2,
        ),
        else_=func.similarity(ProductTranslation.name, query) / 2,
    )

    return (
        select(ProductTranslation.product_id, func.max(relevance).label("relevance"))
        .where(or_(text_match, ProductTranslation.name.bool_op("%")(query)))
        .group_by(ProductTranslation.product_id)
    )


def _filter_conditions(filters: ProductFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.category_codes:
        conditions.append(Product.category.has(Category.code.in_(filters.category_codes)))
    if filters.vendors:
        conditions.append(Product.vendor.has(Vendor.name.in_(filters.vendors)))
    conditions += [
        Product.claims.any(
            and_(
                ProductClaim.claim_type_code == claim_type,
                ProductClaim.claim_element_code == element,
            )
        )
        for claim_type, element in filters.required_claims
    ]
    conditions += [
        Product.diets.any(ProductDiet.diet_code == diet) for diet in filters.required_diets
    ]
    conditions += [
        Product.labels.any(ProductLabel.label_code == label) for label in filters.required_labels
    ]
    if filters.countries_of_origin:
        conditions.append(Product.country_of_origin.in_(filters.countries_of_origin))
    if filters.min_delivery_reliability is not None:
        # NULL compares as unknown, so products without reliability data drop out
        conditions.append(Product.delivery_reliability >= filters.min_delivery_reliability)
    return conditions


async def search_products(
    session: AsyncSession,
    *,
    query: str | None,
    filters: ProductFilters,
    limit: int,
    offset: int,
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
        stmt.where(*_filter_conditions(filters))
        .limit(limit)
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


async def count_products(
    session: AsyncSession, *, query: str | None, filters: ProductFilters
) -> int:
    stmt = select(func.count()).select_from(Product).where(*_filter_conditions(filters))
    if query is not None:
        matches = _matching_product_ids(query).subquery()
        stmt = stmt.join(matches, matches.c.product_id == Product.id)

    return (await session.execute(stmt)).scalar_one()


async def existing_codes(
    session: AsyncSession, column: InstrumentedAttribute[str], codes: Collection[str]
) -> set[str]:
    """
    The subset of `codes` present in `column`, e.g. Diet.code.
    """
    if not codes:
        return set()
    return set((await session.scalars(select(column).where(column.in_(codes)))).all())
