"""
Orders: a commitment made from exactly one quote, kept in Saint Elmo's own order book
because the Valio Aimo API takes no orders.

Placing an order re-checks the quote's lines on fresh Valio Aimo data and judges them
again against the agent's current mandate and period spend. The order follows that new
judgement, whatever the quote said: AUTO_APPROVE is confirmed and placed, NEEDS_HUMAN
waits for an approver, REJECT is rejected.

An approval re-checks once more. The NEEDS_HUMAN reasons and the total the order was
pending with are what the approver accepts; a REJECT reason rejects the order, and a
NEEDS_HUMAN reason the approver hasn't seen or a higher total keeps it pending, now
showing them.

A status is credited to whoever's request led to it: the agent on placing, the
approver on deciding. Placing a confirmed or approved order is the system's.

The quote id is the idempotency key (ADR 0002): one quote gives at most one order.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts.dtos import AuthenticatedUser
from saint_elmo_backend.agents import crud as agent_crud
from saint_elmo_backend.audit import services as audit_services
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.mandates import services as mandate_services
from saint_elmo_backend.mandates.dtos import AgentMandate
from saint_elmo_backend.offers.cache import OfferCache
from saint_elmo_backend.orders import crud
from saint_elmo_backend.orders.changes import order_changes
from saint_elmo_backend.orders.dtos import SYSTEM, Actor
from saint_elmo_backend.orders.enums import OrderStatus
from saint_elmo_backend.orders.exceptions import OrderNotFoundError, OrderNotPendingError
from saint_elmo_backend.orders.models import Order, OrderLine, OrderStatusChange
from saint_elmo_backend.policy.assessment import Assessment, assess
from saint_elmo_backend.policy.dtos import LineRequest
from saint_elmo_backend.policy.enums import PolicyOutcome, Severity
from saint_elmo_backend.quotes import crud as quote_crud
from saint_elmo_backend.quotes import services as quote_services
from saint_elmo_backend.quotes.enums import QuoteStatus
from saint_elmo_backend.quotes.exceptions import (
    QuoteAlreadyOrderedError,
    QuoteExpiredError,
    QuoteNotFoundError,
)
from saint_elmo_backend.quotes.models import Quote
from saint_elmo_backend.valio_aimo.client import ValioAimoClient

# The status an agent's order request leads to, per policy outcome
_STATUS_ON_PLACING = {
    PolicyOutcome.AUTO_APPROVE: OrderStatus.CONFIRMED,
    PolicyOutcome.NEEDS_HUMAN: OrderStatus.PENDING_APPROVAL,
    PolicyOutcome.REJECT: OrderStatus.REJECTED,
}


async def place_order(
    session: AsyncSession,
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    *,
    organization_id: int,
    agent_id: int,
    quote_id: uuid.UUID,
    now: datetime,
    ignore_closing_time: bool = False,
) -> Order:
    """
    Place an order from one of the agent's own quotes.

    Raises `QuoteNotFoundError` for a quote that isn't the agent's,
    `QuoteAlreadyOrderedError` with the existing order, `QuoteExpiredError`,
    `MandateNotFoundError`, and whatever `policy.assessment.assess` raises.

    Records ORDER_REQUESTED, ORDER_RECHECKED and one ORDER_<STATUS> per status entered.
    A composable building block: the caller owns the commit.
    """
    # Locked, so a retry racing the first request waits and then finds its order
    quote = await quote_crud.get_quote(
        session,
        organization_id=organization_id,
        public_id=quote_id,
        agent_id=agent_id,
        for_update=True,
    )
    if quote is None:
        raise QuoteNotFoundError()
    # A retry is told about its order even once the quote has expired
    existing = await crud.get_order_for_quote(
        session, organization_id=organization_id, quote_id=quote.id
    )
    if existing is not None:
        raise QuoteAlreadyOrderedError(existing.public_id)
    if quote_services.quote_status(quote, now) is QuoteStatus.EXPIRED:
        raise QuoteExpiredError()

    agent = await agent_crud.get_agent(session, organization_id=organization_id, agent_id=agent_id)
    assert agent is not None, "the quote's agent is in its buyer organisation"
    mandate = await mandate_services.get_agent_mandate(
        session, organization_id=organization_id, agent_id=agent_id, now=now
    )
    assessment = await _recheck(
        session, valio_aimo, cache, quote, mandate, now=now, ignore_closing_time=ignore_closing_time
    )

    status = _STATUS_ON_PLACING[assessment.outcome]
    order = Order(
        public_id=uuid.uuid4(),
        org_id=organization_id,
        created_at=now,
        quote=quote,
        agent=agent,
        status=status,
        currency=quote.currency,
        lines=[],
        status_history=[],
    )
    _show_assessment(order, assessment)
    session.add(order)
    await session.flush()

    requester = Actor.of_agent(agent)
    await _record(
        session,
        order,
        AuditEventType.ORDER_REQUESTED,
        requester,
        {"quoteId": str(quote.public_id)},
    )
    await _record_recheck(session, order, assessment, requester)
    await _enter(session, order, status, requester, now=now)
    if status is OrderStatus.CONFIRMED:
        await _enter(session, order, OrderStatus.PLACED, SYSTEM, now=now)
    return order


async def get_order(
    session: AsyncSession,
    *,
    organization_id: int,
    public_id: uuid.UUID,
    agent_id: int | None = None,
) -> Order:
    """
    `agent_id` limits it to that agent's own orders. Raises `OrderNotFoundError`.
    """
    order = await crud.get_order(
        session, organization_id=organization_id, public_id=public_id, agent_id=agent_id
    )
    if order is None:
        raise OrderNotFoundError()
    return order


async def list_orders(
    session: AsyncSession,
    *,
    organization_id: int,
    agent_id: int | None = None,
    status: OrderStatus | None = None,
    limit: int,
    offset: int,
) -> tuple[int, list[Order]]:
    """
    The total matching and one page of them, most recent first. `agent_id` limits them
    to that agent's own orders.
    """
    return await crud.list_orders(
        session,
        organization_id=organization_id,
        agent_id=agent_id,
        status=status,
        limit=limit,
        offset=offset,
    )


async def approve_order(
    session: AsyncSession,
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    *,
    organization_id: int,
    approver: AuthenticatedUser,
    public_id: uuid.UUID,
    note: str | None,
    now: datetime,
    ignore_closing_time: bool = False,
) -> Order:
    """
    Re-check a pending order on live data. Its own pending total doesn't count against
    its period spend. Then:

    - a REJECT reason (e.g. the closing time has passed) rejects it;
    - a NEEDS_HUMAN reason it wasn't pending with, or a total above the one it was
      pending with, keeps it PENDING_APPROVAL, showing the new reasons and total, for
      the approver to decide again: an approval never commits more than they saw;
    - otherwise it is APPROVED and PLACED.

    Raises `OrderNotFoundError`, `OrderNotPendingError`, `MandateNotFoundError`, and
    whatever `policy.assessment.assess` raises. A composable building block: the caller
    owns the commit.
    """
    order = await _pending_order(session, organization_id=organization_id, public_id=public_id)
    # What the approver saw and accepts
    accepted = _needs_human_reasons(order.reasons)
    seen_total = order.net_total
    mandate = await mandate_services.get_agent_mandate(
        session,
        organization_id=organization_id,
        agent_id=order.agent_id,
        now=now,
        excluding_order_id=order.id,
    )
    assessment = await _recheck(
        session,
        valio_aimo,
        cache,
        order.quote,
        mandate,
        now=now,
        ignore_closing_time=ignore_closing_time,
    )
    _show_assessment(order, assessment)
    unseen = _needs_human_reasons(order.reasons) - accepted
    total_grew = order.net_total > seen_total

    actor = Actor.of_user(approver)
    decision = {"approver": actor.label, "note": note}
    await _record_recheck(
        session,
        order,
        assessment,
        actor,
        {
            "approval": decision,
            "unseenReasons": [list(reason) for reason in sorted(unseen)],
            "seenTotal": float(seen_total),
        },
    )
    if assessment.outcome is PolicyOutcome.REJECT:
        _record_decision(order, approver, note, now)
        await _enter(session, order, OrderStatus.REJECTED, actor, now=now, details=decision)
    elif not unseen and not total_grew:
        _record_decision(order, approver, note, now)
        await _enter(session, order, OrderStatus.APPROVED, actor, now=now, details=decision)
        await _enter(session, order, OrderStatus.PLACED, SYSTEM, now=now)
    return order


async def reject_order(
    session: AsyncSession,
    *,
    organization_id: int,
    approver: AuthenticatedUser,
    public_id: uuid.UUID,
    note: str | None,
    now: datetime,
) -> Order:
    """
    Raises `OrderNotFoundError` and `OrderNotPendingError`. Records
    ORDER_REJECTED_BY_HUMAN. A composable building block: the caller owns the commit.
    """
    order = await _pending_order(session, organization_id=organization_id, public_id=public_id)
    actor = Actor.of_user(approver)
    _record_decision(order, approver, note, now)
    await _enter(
        session,
        order,
        OrderStatus.REJECTED,
        actor,
        now=now,
        event_type=AuditEventType.ORDER_REJECTED_BY_HUMAN,
        details={"approver": actor.label, "note": note},
    )
    return order


async def _pending_order(
    session: AsyncSession, *, organization_id: int, public_id: uuid.UUID
) -> Order:
    # Locked, so two approvers deciding at once can't both decide it
    order = await crud.get_order(
        session, organization_id=organization_id, public_id=public_id, for_update=True
    )
    if order is None:
        raise OrderNotFoundError()
    if order.status is not OrderStatus.PENDING_APPROVAL:
        raise OrderNotPendingError(order.status)
    return order


def _needs_human_reasons(reasons: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """
    (code, lineRef) of each NEEDS_HUMAN reason; a quote-wide reason has lineRef "".
    """
    return {
        (reason["code"], reason["lineRef"] or "")
        for reason in reasons
        if reason["severity"] == Severity.NEEDS_HUMAN
    }


async def _recheck(
    session: AsyncSession,
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    quote: Quote,
    mandate: AgentMandate,
    *,
    now: datetime,
    ignore_closing_time: bool,
) -> Assessment:
    """
    The quote's lines priced on fresh Valio Aimo data, never the cache, and judged
    against `mandate` as it is now.
    """
    return await assess(
        session,
        valio_aimo,
        cache,
        organization_id=quote.org_id,
        deliver_by=quote.deliver_by,
        lines=[
            LineRequest(
                product_code=line.product_code,
                quantity=line.requested_quantity,
                unit=line.requested_unit,
                substitutes_for=line.substitutes_for,
            )
            for line in quote.lines
        ],
        mandate=mandate,
        now=now,
        ignore_closing_time=ignore_closing_time,
        use_cache=False,
    )


def _show_assessment(order: Order, assessment: Assessment) -> None:
    """
    Make the order show this re-check: its lines, totals, policy and the changes from
    its quote. Lines are updated in place, by position, once they exist.
    """
    totals = assessment.totals
    order.outcome = assessment.outcome
    order.mandate_version = assessment.mandate_version
    order.reasons = assessment.reasons
    order.net_total = totals.net
    order.gross_total = totals.gross
    order.deposits = assessment.deposits
    order.changes = order_changes(
        {str(line.position): line.offer for line in order.quote.lines},
        {line.line_ref: line.offer_json for line in assessment.lines},
    )

    existing = {line.position: line for line in order.lines}
    for priced in assessment.lines:
        line = existing.get(priced.position)
        if line is None:
            line = OrderLine(
                org_id=order.org_id,
                position=priced.position,
                product_code=priced.request.product_code,
                substitutes_for=priced.request.substitutes_for,
                category_code=priced.category_code,
            )
            order.lines.append(line)
        line.net_total = priced.net_total
        line.outcome = assessment.line_outcome(priced)
        line.offer = priced.offer_json
        line.reasons = assessment.line_reasons(priced)


def _record_decision(
    order: Order, approver: AuthenticatedUser, note: str | None, now: datetime
) -> None:
    order.decided_by_user_id = approver.id
    order.decided_at = now
    order.approver_note = note


async def _enter(
    session: AsyncSession,
    order: Order,
    status: OrderStatus,
    actor: Actor,
    *,
    now: datetime,
    event_type: AuditEventType | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Move the order to `status`, append it to its history and record ORDER_<STATUS>
    (or `event_type`).
    """
    order.status = status
    order.status_history.append(
        OrderStatusChange(org_id=order.org_id, status=status, at=now, by=actor.label)
    )
    await _record(
        session,
        order,
        event_type or AuditEventType(f"ORDER_{status}"),
        actor,
        {"status": status.value, "by": actor.label, **(details or {})},
    )


async def _record_recheck(
    session: AsyncSession,
    order: Order,
    assessment: Assessment,
    actor: Actor,
    details: dict[str, Any] | None = None,
) -> None:
    """
    The fresh offers used, the policy result with the mandate version, and what changed
    from the quote, so the judgement can be replayed.
    """
    await _record(
        session,
        order,
        AuditEventType.ORDER_RECHECKED,
        actor,
        {
            "quoteId": str(order.quote.public_id),
            **assessment.audit_record(),
            "totals": {
                "net": float(order.net_total),
                "gross": float(order.gross_total),
                "currency": order.currency,
            },
            "changes": order.changes,
            **(details or {}),
        },
    )


async def _record(
    session: AsyncSession,
    order: Order,
    event_type: AuditEventType,
    actor: Actor,
    payload: dict[str, Any],
) -> None:
    await audit_services.record_event(
        session,
        organization_id=order.org_id,
        event_type=event_type,
        agent_id=actor.agent_id,
        user_id=actor.user_id,
        subject_public_id=order.public_id,
        payload={"orderId": str(order.public_id), **payload},
    )
