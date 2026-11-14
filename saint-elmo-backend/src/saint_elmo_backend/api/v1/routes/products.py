from typing import Annotated

from fastapi import APIRouter, Depends, Query

from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.api.exceptions import (
    InvalidCredentials,
    PermissionDenied,
    ProductNotFound,
    UnknownFilterCodes,
    to_response_error,
)
from saint_elmo_backend.api.v1.auth import authenticate
from saint_elmo_backend.catalog import services
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.catalog.exceptions import ProductNotFoundError, UnknownCodesError
from saint_elmo_backend.catalog.schemas import (
    ProductDetailResponse,
    ProductSearchRequest,
    ProductSearchResponse,
)

router = APIRouter(
    dependencies=[Depends(authenticate(users=True, agent_scope=Scope.CATALOG_READ))],
    responses=to_response_error(InvalidCredentials, PermissionDenied),
)


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
        raise UnknownFilterCodes.for_request(ProductSearchRequest, exc.unknown) from exc

    return ProductSearchResponse.from_result(result)


@router.get(
    "/{code}",
    response_model=ProductDetailResponse,
    responses=to_response_error(ProductNotFound),
)
async def get_product(
    code: str,
    session: ASession,
    language: Annotated[
        Language,
        Query(description="Language of name fields; falls back to fi when missing"),
    ] = Language.EN,
) -> ProductDetailResponse:
    try:
        detail = await services.get_product(session, code=code, language=language)
    except ProductNotFoundError as exc:
        raise ProductNotFound() from exc
    return ProductDetailResponse.from_detail(detail)
