from fastapi import APIRouter

from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.catalog import services
from saint_elmo_backend.catalog.schemas import ProductSearchRequest, ProductSearchResponse

router = APIRouter()


# TODO(#7): require auth once the auth ticket lands; the catalogue is global, non-tenant data
@router.post("/search", response_model=ProductSearchResponse)
async def search_products(
    data: ProductSearchRequest, session: ASession
) -> ProductSearchResponse:
    result = await services.search_products(
        session, language=data.language, limit=data.limit, offset=data.offset
    )
    return ProductSearchResponse.from_result(result)
