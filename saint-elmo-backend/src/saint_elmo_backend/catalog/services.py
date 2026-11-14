from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.catalog import crud
from saint_elmo_backend.catalog.dtos import (
    CatalogProvenance,
    ProductSearchHit,
    ProductSearchResult,
)
from saint_elmo_backend.catalog.enums import Language
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
