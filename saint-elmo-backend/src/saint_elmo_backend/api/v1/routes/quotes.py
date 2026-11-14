from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, status
from loguru import logger
from pydantic import UUID4

from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.api.annotations import AOfferCache, ASession, AValioAimoClient
from saint_elmo_backend.api.exceptions import (
    CustomerNumberMissing,
    InvalidCredentials,
    MandateNotFound,
    PermissionDenied,
    QuoteNotFound,
    UnknownProducts,
    ValioAimoApiUnavailable,
    to_response_error,
)
from saint_elmo_backend.api.v1.auth import Principal, authenticate
from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.mandates.exceptions import MandateNotFoundError
from saint_elmo_backend.offers.exceptions import CustomerNumberMissingError, UnknownProductsError
from saint_elmo_backend.quotes import services
from saint_elmo_backend.quotes.exceptions import QuoteNotFoundError
from saint_elmo_backend.quotes.schemas import QuoteIn, QuoteResponse
from saint_elmo_backend.valio_aimo.exceptions import ValioAimoError

router = APIRouter(responses=to_response_error(InvalidCredentials, PermissionDenied))

AgentPrincipal = Annotated[Principal, Depends(authenticate(agent_scope=Scope.QUOTE_CREATE))]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=QuoteResponse,
    summary="Quote lines against the agent's mandate",
    description="Converts each line to sales units, prices it from live offers on "
    "`deliverBy` and judges the quote against the calling agent's mandate. The policy "
    "outcome says what placing an order would give if live data hasn't changed. A quote "
    "is created whatever the outcome, REJECT included: revise from its reasons and quote "
    "again with `previousQuoteId`. `buyerRequest` and `rationale` are kept and shown to "
    "approvers but never affect the outcome. The quote expires at `expiresAt`.",
    responses=to_response_error(
        UnknownProducts,
        QuoteNotFound,
        MandateNotFound,
        CustomerNumberMissing,
        ValioAimoApiUnavailable,
    ),
)
async def create_quote(
    data: QuoteIn,
    principal: AgentPrincipal,
    session: ASession,
    valio_aimo: AValioAimoClient,
    cache: AOfferCache,
) -> QuoteResponse:
    assert principal.agent is not None
    settings = get_settings()
    now = datetime.now(UTC)
    try:
        quote = await services.create_quote(
            session,
            valio_aimo,
            cache,
            organization_id=principal.organization.id,
            agent_id=principal.agent.id,
            request=data.to_quote_request(),
            now=now,
            ttl=timedelta(minutes=settings.quote_ttl_minutes),
            ignore_closing_time=settings.offers_ignore_closing_time,
        )
    except UnknownProductsError as exc:
        raise UnknownProducts.for_codes(exc.codes) from exc
    except QuoteNotFoundError as exc:
        raise QuoteNotFound("No previous quote with this id in your buyer organisation") from exc
    except MandateNotFoundError as exc:
        raise MandateNotFound() from exc
    except CustomerNumberMissingError as exc:
        raise CustomerNumberMissing() from exc
    except ValioAimoError as exc:
        logger.warning("Valio Aimo API unavailable for a quote: {}", exc)
        raise ValioAimoApiUnavailable() from exc

    await session.commit()
    return QuoteResponse.from_quote(quote, services.quote_status(quote, now))


@router.get(
    "/{quote_id}",
    response_model=QuoteResponse,
    summary="Read a quote",
    description="A quote of the caller's buyer organisation, exactly as it was quoted. "
    "After `expiresAt` its status is EXPIRED.",
    responses=to_response_error(QuoteNotFound),
)
async def get_quote(quote_id: UUID4, principal: AgentPrincipal, session: ASession) -> QuoteResponse:
    try:
        quote = await services.get_quote(
            session, organization_id=principal.organization.id, public_id=quote_id
        )
    except QuoteNotFoundError as exc:
        raise QuoteNotFound() from exc
    return QuoteResponse.from_quote(quote, services.quote_status(quote, datetime.now(UTC)))
