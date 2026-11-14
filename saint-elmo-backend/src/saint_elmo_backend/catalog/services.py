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
    product_ids = await crud.search_product_ids(session, limit=limit, offset=offset)
    total = await crud.count_products(session)
    # NOTE(sw): Getting product info loses the search order so we need to bring it back here put the products back in it
    # TODO(sw): would it not be better to just have a "search_products" crud function instead to avoid this?
    products_by_id = {
        product.id: product for product in await crud.load_products(session, product_ids)
    }
    return ProductSearchResult(
        total=total,
        products=[products_by_id[product_id] for product_id in product_ids],
        provenance=catalog_provenance(),
    )
