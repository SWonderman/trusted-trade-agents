"""
Quotes: an agent's quote lines converted, priced from live offers and judged by
the policy against the agent's mandate, valid until the quote expires.

A quote is created whatever the policy says: a REJECT outcome is an answer the agent
revises from, not an error. The buyer request and rationale are stored and echoed,
and never reach the policy (ADR 0002).
"""

import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.audit import services as audit_services
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.mandates import services as mandate_services
from saint_elmo_backend.offers.cache import OfferCache
from saint_elmo_backend.policy.assessment import Assessment, assess
from saint_elmo_backend.quotes import crud
from saint_elmo_backend.quotes.dtos import QuoteRequest
from saint_elmo_backend.quotes.enums import QuoteStatus
from saint_elmo_backend.quotes.exceptions import QuoteNotFoundError
from saint_elmo_backend.quotes.models import Quote, QuoteLine
from saint_elmo_backend.valio_aimo.client import ValioAimoClient

# Every Valio Aimo price is in euros
QUOTE_CURRENCY = "EUR"


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
        session, organization_id=organization_id, agent_id=agent_id, now=now
    )
    assessment = await assess(
        session,
        valio_aimo,
        cache,
        organization_id=organization_id,
        deliver_by=request.deliver_by,
        lines=request.lines,
        mandate=mandate,
        now=now,
        ignore_closing_time=ignore_closing_time,
    )
    totals = assessment.totals
    quote = Quote(
        public_id=uuid.uuid4(),
        org_id=organization_id,
        agent_id=agent_id,
        created_at=now,
        expires_at=quote_expiry(
            now, ttl, (line.offer.provenance.valid_until for line in assessment.lines)
        ),
        deliver_by=request.deliver_by,
        previous_quote=previous,
        buyer_request=request.buyer_request,
        rationale=request.rationale,
        outcome=assessment.outcome,
        mandate_version=assessment.mandate_version,
        reasons=assessment.reasons,
        net_total=totals.net,
        gross_total=totals.gross,
        currency=QUOTE_CURRENCY,
        deposits=assessment.deposits,
        lines=[
            QuoteLine(
                org_id=organization_id,
                position=line.position,
                product_code=line.request.product_code,
                substitutes_for=line.request.substitutes_for,
                requested_quantity=line.request.quantity,
                requested_unit=line.request.unit,
                outcome=assessment.line_outcome(line),
                offer=line.offer_json,
                reasons=assessment.line_reasons(line),
            )
            for line in assessment.lines
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
        payload=_audit_payload(quote, request, assessment),
    )
    return quote


async def get_quote(session: AsyncSession, *, organization_id: int, public_id: uuid.UUID) -> Quote:
    quote = await crud.get_quote(session, organization_id=organization_id, public_id=public_id)
    if quote is None:
        raise QuoteNotFoundError()
    return quote


def _audit_payload(quote: Quote, request: QuoteRequest, assessment: Assessment) -> dict[str, Any]:
    """
    The full request, the offers used with their conversions and provenance, and the
    policy result with the mandate version, so the judgement can be replayed. In the
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
        **assessment.audit_record(),
        "totals": {
            "net": float(quote.net_total),
            "gross": float(quote.gross_total),
            "currency": quote.currency,
        },
        "expiresAt": quote.expires_at.isoformat(),
    }
