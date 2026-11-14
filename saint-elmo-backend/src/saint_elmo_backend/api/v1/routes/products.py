from fastapi import APIRouter

from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.api.exceptions import UnknownFilterCodes, to_response_error
from saint_elmo_backend.catalog import services
from saint_elmo_backend.catalog.exceptions import UnknownCodesError
from saint_elmo_backend.catalog.schemas import ProductSearchRequest, ProductSearchResponse

router = APIRouter()


# TODO(#7): require auth once the auth ticket lands; the catalogue is global, non-tenant data
@router.post(
    "/search",
    response_model=ProductSearchResponse,
    responses=to_response_error(UnknownFilterCodes),
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
        # Named by request field, so the agent can map each code back to its filter
        fields = ProductSearchRequest.model_fields
        raise UnknownFilterCodes.for_filters(
            {fields[name].alias or name: codes for name, codes in exc.unknown.items()}
        ) from exc

    return ProductSearchResponse.from_result(result)
