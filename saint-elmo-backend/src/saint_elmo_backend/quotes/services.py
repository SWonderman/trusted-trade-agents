"""
Quotes: an agent's quote lines converted, priced from live offers and judged by
the policy against the agent's mandate, valid until the quote expires.

A quote is created whatever the policy says: a REJECT outcome is an answer the agent
revises from, not an error. The buyer request and rationale are stored and echoed,
and never reach the policy (ADR 0002).
"""

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.audit import services as audit_services
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.catalog import crud as catalog_crud
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.mandates import services as mandate_services
from saint_elmo_backend.offers import services as offer_services
from saint_elmo_backend.offers.cache import OfferCache
from saint_elmo_backend.offers.dtos import OfferLine, RequestedProduct
from saint_elmo_backend.offers.exceptions import UnknownProductsError
from saint_elmo_backend.offers.schemas import OfferOut
from saint_elmo_backend.policy.dtos import (
    PolicyInput,
    PolicyJudgement,
    PolicyLine,
    SubstitutedProduct,
)
from saint_elmo_backend.policy.engine import evaluate
from saint_elmo_backend.policy.facts import line_offer, product_facts
from saint_elmo_backend.quotes import crud
from saint_elmo_backend.quotes.dtos import QuoteLineRequest, QuoteRequest
from saint_elmo_backend.quotes.enums import QuoteStatus
from saint_elmo_backend.quotes.exceptions import QuoteNotFoundError
from saint_elmo_backend.quotes.models import Quote, QuoteLine
from saint_elmo_backend.quotes.schemas import DepositOut, PolicyReasonOut
from saint_elmo_backend.valio_aimo.client import ValioAimoClient

# Every Valio Aimo price is in euros
QUOTE_CURRENCY = "EUR"


@dataclass(frozen=True, slots=True)
class _PricedLine:
    # The line's 1-based position, which is also its line ref in policy reasons
    position: int
    request: QuoteLineRequest
    offer: OfferLine
    # The offer for the product it is a substitute for, at the same quantity
    substituted_offer: OfferLine | None

    @property
    def line_ref(self) -> str:
        return str(self.position)


def quote_expiry(
    created_at: datetime, ttl: timedelta, offer_deadlines: Iterable[datetime | None]
) -> datetime:
    """
    The earliest of `created_at + ttl` and the lines' offer deadlines (each the sooner
    of its price's validTo and its closing time for deliverBy; None when neither is known).

    A deadline already passed doesn't count: the policy rejects that line, and the new
    quote still starts QUOTED so the agent can read why.
    """
    upcoming = (d for d in offer_deadlines if d is not None and d > created_at)
    return min([created_at + ttl, *upcoming])


def quote_status(quote: Quote, now: datetime) -> QuoteStatus:
    return QuoteStatus.EXPIRED if now >= quote.expires_at else QuoteStatus.QUOTED


async def create_quote(
    session: AsyncSession,
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    *,
    organization_id: int,
    agent_id: int,
    request: QuoteRequest,
    now: datetime,
    ttl: timedelta,
    ignore_closing_time: bool = False,
) -> Quote:
    """
    Raises `QuoteNotFoundError` for a `previous_quote_id` outside the buyer
    organization, `MandateNotFoundError`, `UnknownProductsError` listing every unknown
    code (substituted products included), and whatever `offers.services.get_offers` raises.

    Records QUOTE_CREATED. A composable building block: the caller owns the commit.
    """
    previous = None
    if request.previous_quote_id is not None:
        previous = await crud.get_quote(
            session, organization_id=organization_id, public_id=request.previous_quote_id
        )
        if previous is None:
            raise QuoteNotFoundError()

    mandate = await mandate_services.get_agent_mandate(
        session, organization_id=organization_id, agent_id=agent_id
    )

    codes = list(
        dict.fromkeys(
            code
            for line in request.lines
            for code in (line.product_code, line.substitutes_for)
            if code is not None
        )
    )
    products = {p.code: p for p in await catalog_crud.get_products_with_facts(session, codes)}
    if unknown := [code for code in codes if code not in products]:
        raise UnknownProductsError(unknown)

    lines = await _price_lines(
        session,
        valio_aimo,
        cache,
        organization_id=organization_id,
        request=request,
        now=now,
        ignore_closing_time=ignore_closing_time,
    )
    judgement = evaluate(
        PolicyInput(
            mandate=mandate.terms,
            lines=tuple(
                PolicyLine(
                    line_ref=line.line_ref,
                    product=product_facts(products[line.request.product_code]),
                    offer=line_offer(line.offer),
                    substitutes_for=(
                        SubstitutedProduct(
                            line.substituted_offer.product.code, line_offer(line.substituted_offer)
                        )
                        if line.substituted_offer is not None
                        else None
                    ),
                )
                for line in lines
            ),
            deliver_by=request.deliver_by,
            period_spend=mandate.period_spend.committed,
        )
    )

    reasons = [
        PolicyReasonOut.from_reason(reason).model_dump(mode="json", by_alias=True)
        for reason in judgement.reasons
    ]
    line_outcomes = {outcome.line_ref: outcome.outcome for outcome in judgement.lines}
    totals = [line.offer.quantity.line_total for line in lines if line.offer.quantity]
    quote = Quote(
        public_id=uuid.uuid4(),
        org_id=organization_id,
        agent_id=agent_id,
        created_at=now,
        expires_at=quote_expiry(now, ttl, (line.offer.provenance.valid_until for line in lines)),
        deliver_by=request.deliver_by,
        previous_quote=previous,
        buyer_request=request.buyer_request,
        rationale=request.rationale,
        outcome=judgement.outcome,
        mandate_version=mandate.version,
        reasons=reasons,
        net_total=sum((total.net for total in totals if total), Decimal(0)),
        gross_total=sum((total.gross for total in totals if total), Decimal(0)),
        currency=QUOTE_CURRENCY,
        deposits=_deposits(line.offer for line in lines),
        lines=[
            QuoteLine(
                org_id=organization_id,
                position=line.position,
                product_code=line.request.product_code,
                substitutes_for=line.request.substitutes_for,
                requested_quantity=line.request.quantity,
                requested_unit=line.request.unit,
                outcome=line_outcomes[line.line_ref],
                offer=_offer_json(line.offer),
                reasons=[r for r in reasons if r["lineRef"] == line.line_ref],
            )
            for line in lines
        ],
    )
    session.add(quote)
    await session.flush()

    await audit_services.record_event(
        session,
        organization_id=organization_id,
        event_type=AuditEventType.QUOTE_CREATED,
        agent_id=agent_id,
        subject_public_id=quote.public_id,
        payload=_audit_payload(quote, request, lines, judgement),
    )
    return quote


async def get_quote(session: AsyncSession, *, organization_id: int, public_id: uuid.UUID) -> Quote:
    quote = await crud.get_quote(session, organization_id=organization_id, public_id=public_id)
    if quote is None:
        raise QuoteNotFoundError()
    return quote


async def _price_lines(
    session: AsyncSession,
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    *,
    organization_id: int,
    request: QuoteRequest,
    now: datetime,
    ignore_closing_time: bool,
) -> list[_PricedLine]:
    """
    One offers request for every line and every substituted product. A substituted
    product is priced for the line's quantity, so the policy can compare the two per
    buyer unit.
    """
    substituted = [
        RequestedProduct(line.substitutes_for, line.quantity, line.unit)
        for line in request.lines
        if line.substitutes_for is not None
    ]
    offers = await offer_services.get_offers(
        session,
        valio_aimo,
        cache,
        organization_id=organization_id,
        deliver_by=request.deliver_by,
        requested=[
            *(
                RequestedProduct(line.product_code, line.quantity, line.unit)
                for line in request.lines
            ),
            *substituted,
        ],
        language=Language.EN,
        now=now,
        ignore_closing_time=ignore_closing_time,
    )
    # Offers come back in request order: the lines', then the substituted products'
    line_offers = offers.lines[: len(request.lines)]
    substituted_offers = iter(offers.lines[len(request.lines) :])
    return [
        _PricedLine(
            position=position,
            request=line,
            offer=offer,
            substituted_offer=next(substituted_offers) if line.substitutes_for else None,
        )
        for position, (line, offer) in enumerate(zip(request.lines, line_offers, strict=True), 1)
    ]


def _deposits(offers: Iterable[OfferLine]) -> list[dict[str, Any]]:
    """
    Returnable packaging per material and unit, summed over the lines' sales units.
    """
    amounts: dict[tuple[str, str], Decimal] = {}
    for offer in offers:
        sales_units = offer.quantity.converted.sales_units if offer.quantity else None
        if sales_units is None:
            continue
        for deposit in offer.product.deposits:
            key = (deposit.material_code, deposit.unit)
            amounts[key] = amounts.get(key, Decimal(0)) + deposit.quantity * sales_units
    return [
        DepositOut(material_code=material, quantity=quantity, unit=unit).model_dump(
            mode="json", by_alias=True
        )
        for (material, unit), quantity in amounts.items()
    ]


def _offer_json(offer: OfferLine) -> dict[str, Any]:
    return OfferOut.from_line(offer).model_dump(mode="json", by_alias=True)


def _audit_payload(
    quote: Quote,
    request: QuoteRequest,
    lines: Sequence[_PricedLine],
    judgement: PolicyJudgement,
) -> dict[str, Any]:
    """
    The full request, the offers used with their conversions and provenance, and the
    policy result with the mandate version, so the judgment can be replayed. In the
    API's JSON shape: amounts as numbers, camelCase keys.
    """
    return {
        "quoteId": str(quote.public_id),
        "request": {
            "deliverBy": request.deliver_by.isoformat(),
            "lines": [
                {
                    "productCode": line.product_code,
                    "quantity": float(line.quantity),
                    "unit": line.unit,
                    "substitutesFor": line.substitutes_for,
                }
                for line in request.lines
            ],
            "buyerRequest": request.buyer_request,
            "rationale": request.rationale,
            "previousQuoteId": str(request.previous_quote_id)
            if request.previous_quote_id
            else None,
        },
        "lines": [
            {
                "lineRef": line.line_ref,
                "offer": _offer_json(line.offer),
                "substitutedOffer": _offer_json(line.substituted_offer)
                if line.substituted_offer
                else None,
            }
            for line in lines
        ],
        "policy": {
            "outcome": judgement.outcome.value,
            "reasons": quote.reasons,
            "mandateVersion": quote.mandate_version,
            "lines": [
                {"lineRef": outcome.line_ref, "outcome": outcome.outcome.value}
                for outcome in judgement.lines
            ],
        },
        "totals": {
            "net": float(quote.net_total),
            "gross": float(quote.gross_total),
            "currency": quote.currency,
        },
        "expiresAt": quote.expires_at.isoformat(),
    }
