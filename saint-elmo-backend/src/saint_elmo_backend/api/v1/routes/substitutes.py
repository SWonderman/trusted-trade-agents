from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from loguru import logger

from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.api.annotations import AOfferCache, ASession, AValioAimoClient
from saint_elmo_backend.api.exceptions import (
    CustomerNumberMissing,
    InvalidCredentials,
    MandateNotFound,
    PermissionDenied,
    ProductNotFound,
    UnknownFilterCodes,
    ValioAimoApiUnavailable,
    to_response_error,
)
from saint_elmo_backend.api.v1.auth import Principal, authenticate
from saint_elmo_backend.catalog.exceptions import ProductNotFoundError, UnknownCodesError
from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.mandates.exceptions import MandateNotFoundError
from saint_elmo_backend.offers.exceptions import CustomerNumberMissingError
from saint_elmo_backend.substitutes import services
from saint_elmo_backend.substitutes.schemas import SubstitutesIn, SubstitutesResponse
from saint_elmo_backend.valio_aimo.exceptions import ValioAimoError

# Mounted under /products, beside the catalogue routes, but for agents only
router = APIRouter(responses=to_response_error(InvalidCredentials, PermissionDenied))

AgentPrincipal = Annotated[Principal, Depends(authenticate(agent_scope=Scope.OFFERS_READ))]


@router.post(
    "/{code}/substitutes",
    response_model=SubstitutesResponse,
    summary="Ranked substitutes for a product that can't meet the need",
    description="""Ranks substitutes for the product, labelled BEST, BETTER, then GOOD.
It only ranks: choosing one and quoting it with `substitutesFor` is the agent's decision.

**Candidates**: the product's curated substitutes, then products in its category, that
meet the calling agent's mandate requirements (claims, labels, diets, allergen exclusions,
origins, delivery reliability) plus the request's filters, which can only narrow them.
Blocked categories and vendors are left out; ones merely not on the mandate's allowed
lists stay, and their `policyPreview` says a human must decide.
They must be expressible in the buyer unit: both in L, both in KG, or in the same sales
unit. Live offers are fetched for at most 50 of them.

**Score** out of 100, in this order of importance:

| Input | Points |
| --- | --- |
| Delivery | 20 for meeting `deliverBy`, 20 for covering the quantity (unknown stock counts) |
| Price per buyer unit | 30 × cheapest candidate's / this one's; 0 when unknown |
| Delivery reliability | 15 × reliability; unknown counts as the candidates' mean |
| Labels gained | 5 per label the original lacks, at most 2 |
| CO₂ estimate | 5 × lowest candidate's / this one's; unknown counts as the mean |

Delivery comes first outright: candidates are ordered by how many of the two delivery
conditions they meet, then by score, so nothing lifts a late or short candidate above one
that delivers. Equal scores rank curated substitutes first, then by product code.

`policyPreview` judges each candidate as a substitute line for the original, as a quote
would now. No candidates is a 200 with `NO_SUBSTITUTES_FOUND`.""",
    responses=to_response_error(
        ProductNotFound,
        MandateNotFound,
        UnknownFilterCodes,
        CustomerNumberMissing,
        ValioAimoApiUnavailable,
    ),
)
async def find_substitutes(
    code: str,
    principal: AgentPrincipal,
    session: ASession,
    valio_aimo: AValioAimoClient,
    cache: AOfferCache,
    data: SubstitutesIn | None = None,
) -> SubstitutesResponse:
    assert principal.agent is not None
    data = data or SubstitutesIn()
    try:
        substitutes = await services.find_substitutes(
            session,
            valio_aimo,
            cache,
            organization_id=principal.organization.id,
            agent_id=principal.agent.id,
            product_code=code,
            request=data.to_request(),
            now=datetime.now(UTC),
            ignore_closing_time=get_settings().offers_ignore_closing_time,
        )
    except ProductNotFoundError as exc:
        raise ProductNotFound() from exc
    except UnknownCodesError as exc:
        raise UnknownFilterCodes.for_request(SubstitutesIn, exc.unknown) from exc
    except MandateNotFoundError as exc:
        raise MandateNotFound() from exc
    except CustomerNumberMissingError as exc:
        raise CustomerNumberMissing() from exc
    except ValioAimoError as exc:
        logger.warning("Valio Aimo API unavailable for substitutes: {}", exc)
        raise ValioAimoApiUnavailable() from exc

    await session.commit()
    return SubstitutesResponse.from_substitutes(substitutes)
