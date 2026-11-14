from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.catalog import crud
from saint_elmo_backend.catalog.schemas import (
    ProductHit,
    ProductSearchRequest,
    ProductSearchResponse,
    Provenance,
)
from saint_elmo_backend.core.settings import get_settings

CATALOG_SOURCE = "Valio Aimo static catalog + GS1 Synkka"


def catalog_provenance() -> Provenance:
    return Provenance(
        source=CATALOG_SOURCE,
        catalog_snapshot_date=get_settings().catalog_snapshot_date,
    )


async def search_products(
    session: AsyncSession, data: ProductSearchRequest
) -> ProductSearchResponse:
    product_ids = await crud.search_product_ids(session, limit=data.limit, offset=data.offset)
    total = await crud.count_products(session)
    products = await crud.load_products(session, product_ids)
    return ProductSearchResponse(
        total=total,
        items=[ProductHit.from_product(product, data.language) for product in products],
        provenance=catalog_provenance(),
    )
