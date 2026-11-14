from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from loguru import logger

from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.api.annotations import AOfferCache, ASession, AValioAimoClient
from saint_elmo_backend.api.exceptions import (
    CustomerNumberMissing,
    InvalidCredentials,
    PermissionDenied,
    UnknownProducts,
    ValioAimoApiUnavailable,
    to_response_error,
)
from saint_elmo_backend.api.v1.auth import Principal, authenticate
from saint_elmo_backend.offers import services
from saint_elmo_backend.offers.exceptions import CustomerNumberMissingError, UnknownProductsError
from saint_elmo_backend.offers.schemas import OffersRequest, OffersResponse
from saint_elmo_backend.valio_aimo.exceptions import ValioAimoError

router = APIRouter(responses=to_response_error(InvalidCredentials, PermissionDenied))

AgentPrincipal = Annotated[Principal, Depends(authenticate(agent_scope=Scope.OFFERS_READ))]


@router.post(
    "",
    response_model=OffersResponse,
    summary="Live price and availability for a shortlist of products",
    description="Price and availability from the Valio Aimo API for the listed products on "
    "`deliverBy`, priced for the caller's buyer organisation. With a quantity, the line is "
    "converted to whole sales units (rounded up, then to the lot size) and totalled. "
    "Shortfalls and data gaps come as reason codes; an offer is binding on nothing.",
    responses=to_response_error(UnknownProducts, CustomerNumberMissing, ValioAimoApiUnavailable),
)
async def get_offers(
    data: OffersRequest,
    principal: AgentPrincipal,
    session: ASession,
    valio_aimo: AValioAimoClient,
    cache: AOfferCache,
) -> OffersResponse:
    try:
        offers = await services.get_offers(
            session,
            valio_aimo,
            cache,
            organization_id=principal.organization.id,
            deliver_by=data.deliver_by,
            items=[item.to_item() for item in data.items],
            language=data.language,
            now=datetime.now(UTC),
        )
    except UnknownProductsError as exc:
        raise UnknownProducts.for_codes(exc.codes) from exc
    except CustomerNumberMissingError as exc:
        raise CustomerNumberMissing() from exc
    except ValioAimoError as exc:
        logger.warning("Valio Aimo API unavailable for offers: {}", exc)
        raise ValioAimoApiUnavailable() from exc

    return OffersResponse.from_offers(offers)
