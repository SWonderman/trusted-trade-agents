from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.catalog import crud
from saint_elmo_backend.catalog.dtos import CatalogProvenance, ProductSearchResult
from saint_elmo_backend.core.settings import get_settings

CATALOG_SOURCE = "Valio Aimo static catalog + GS1 Synkka"


def catalog_provenance() -> CatalogProvenance:
    return CatalogProvenance(
        source=CATALOG_SOURCE,
        catalog_snapshot_date=get_settings().catalog_snapshot_date,
    )


async def search_products(
    session: AsyncSession, *, limit: int, offset: int
) -> ProductSearchResult:
    products = await crud.search_products(session, limit=limit, offset=offset)
    total = await crud.count_products(session)
    return ProductSearchResult(
        total=total, products=products, provenance=catalog_provenance()
    )
