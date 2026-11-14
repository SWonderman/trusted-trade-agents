from fastapi import APIRouter

from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.api.exceptions import UnknownCode, to_response_error
from saint_elmo_backend.catalog import services
from saint_elmo_backend.catalog.exceptions import UnknownCodesError
from saint_elmo_backend.catalog.schemas import ProductSearchRequest, ProductSearchResponse
from saint_elmo_backend.core.schema import camelize

router = APIRouter()


# TODO(#7): require auth once the auth ticket lands; the catalogue is global, non-tenant data
@router.post(
    "/search",
    response_model=ProductSearchResponse,
    responses=to_response_error(UnknownCode),
)
async def search_products(data: ProductSearchRequest, session: ASession) -> ProductSearchResponse:
    try:
        result = await services.search_products(
            session,
            query=data.query,
            filters=data.to_filters(),
            language=data.language,
            limit=data.limit,
            offset=data.offset,
        )
    except UnknownCodesError as exc:
        unknown = ", ".join(
            f"{camelize(name)}=[{', '.join(codes)}]" for name, codes in exc.unknown.items()
        )
        raise UnknownCode(f"Unknown codes: {unknown}") from exc

    return ProductSearchResponse.from_result(result)
