from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.catalog import crud
from saint_elmo_backend.catalog.dtos import (
    CatalogProvenance,
    CuratedSubstitute,
    ProductDetail,
    ProductSearchHit,
    ProductSearchResult,
)
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.catalog.exceptions import ProductNotFoundError
from saint_elmo_backend.catalog.models import Product
from saint_elmo_backend.core.settings import get_settings

CATALOG_SOURCE = "Valio Aimo static catalog + GS1 Synkka"


def catalog_provenance() -> CatalogProvenance:
    return CatalogProvenance(
        source=CATALOG_SOURCE,
        catalog_snapshot_date=get_settings().catalog_snapshot_date,
    )


def product_name(product: Product, language: Language) -> str | None:
    names = {translation.language: translation.name for translation in product.translations}
    # Fall back to Finnish when no name was found
    return names.get(language) or names.get(Language.FI)


async def search_products(
    session: AsyncSession,
    *,
    query: str | None,
    language: Language,
    limit: int,
    offset: int,
) -> ProductSearchResult:
    # A blank search is still treated as a search
    if query is not None and not query.strip():
        query = None

    matches = await crud.search_products(session, query=query, limit=limit, offset=offset)
    total = await crud.count_products(session, query=query)

    return ProductSearchResult(
        total=total,
        hits=[
            ProductSearchHit(
                product=match.product,
                name=product_name(match.product, language),
                relevance=match.relevance,
            )
            for match in matches
        ],
        provenance=catalog_provenance(),
    )


async def get_product(session: AsyncSession, *, code: str, language: Language) -> ProductDetail:
    product = await crud.get_product_by_code(session, code)
    if product is None:
        raise ProductNotFoundError(code)

    return ProductDetail(
        product=product,
        name=product_name(product, language),
        curated_substitutes=sorted(
            (
                CuratedSubstitute(
                    code=substitution.substitute.code,
                    name=product_name(substitution.substitute, language),
                )
                for substitution in product.substitutions
            ),
            key=lambda substitute: substitute.code,
        ),
        provenance=catalog_provenance(),
    )
