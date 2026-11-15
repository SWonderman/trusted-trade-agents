from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from loguru import logger
from pydantic import UUID4

from saint_elmo_backend.accounts.dtos import AuthenticatedUser
from saint_elmo_backend.accounts.enums import Permission
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.api.annotations import AOfferCache, ASession, AValioAimoClient
from saint_elmo_backend.api.exceptions import (
    CustomerNumberMissing,
    InvalidCredentials,
    MandateNotFound,
    OrderNotFound,
    OrderNotPending,
    PermissionDenied,
    QuoteAlreadyOrdered,
    QuoteExpired,
    QuoteNotFound,
    UnknownProducts,
    ValioAimoApiUnavailable,
    to_response_error,
)
from saint_elmo_backend.api.v1.auth import (
    AuditReader,
    Principal,
    authenticate,
    require_permission,
)
from saint_elmo_backend.audit import trail
from saint_elmo_backend.audit.schemas import AuditEventOut, OrderTrailResponse
from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.mandates.exceptions import MandateNotFoundError
from saint_elmo_backend.offers.exceptions import CustomerNumberMissingError, UnknownProductsError
from saint_elmo_backend.orders import services
from saint_elmo_backend.orders.enums import OrderStatus
from saint_elmo_backend.orders.exceptions import OrderNotFoundError, OrderNotPendingError
from saint_elmo_backend.orders.schemas import DecisionIn, OrderIn, OrderListResponse, OrderResponse
from saint_elmo_backend.quotes.exceptions import (
    QuoteAlreadyOrderedError,
    QuoteExpiredError,
    QuoteNotFoundError,
)
from saint_elmo_backend.valio_aimo.exceptions import ValioAimoError

router = APIRouter(responses=to_response_error(InvalidCredentials, PermissionDenied))

OrderingAgent = Annotated[Principal, Depends(authenticate(agent_scope=Scope.ORDER_PLACE))]
# An agent reads its own orders; a user reads the buyer organisation's
OrderReader = Annotated[Principal, Depends(authenticate(users=True, agent_scope=Scope.ORDER_READ))]
# Users only: no Agent token can approve, whatever its scopes, and there is no approve scope
Approver = Annotated[AuthenticatedUser, Depends(require_permission(Permission.ORDER_APPROVE))]

# Errors from re-checking live data, when placing and when approving
_RECHECK_ERRORS = (MandateNotFound, UnknownProducts, CustomerNumberMissing, ValioAimoApiUnavailable)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=OrderResponse,
    summary="Place an order from a quote",
    description="Re-checks every line of the quote on fresh Valio Aimo data and judges "
    "it again against the agent's current mandate and period spend; the order follows "
    "that result, which `changes` explains when live data moved since the quote. "
    "AUTO_APPROVE is placed at once (CONFIRMED, then PLACED). NEEDS_HUMAN waits as "
    "PENDING_APPROVAL: poll `GET /orders/{orderId}` after `checkAgainAfterSeconds`. "
    "REJECT gives a REJECTED order with its reasons, still a 201. The quote id is the "
    "idempotency key: a retry gets 409 QUOTE_ALREADY_ORDERED with the existing "
    "`orderId` in `details`, and never a second order.",
    responses=to_response_error(QuoteNotFound, QuoteExpired, QuoteAlreadyOrdered, *_RECHECK_ERRORS),
)
async def place_order(
    data: OrderIn,
    principal: OrderingAgent,
    session: ASession,
    valio_aimo: AValioAimoClient,
    cache: AOfferCache,
) -> OrderResponse:
    assert principal.agent is not None
    try:
        order = await services.place_order(
            session,
            valio_aimo,
            cache,
            organization_id=principal.organization.id,
            agent_id=principal.agent.id,
            quote_id=data.quote_id,
            now=datetime.now(UTC),
            ignore_closing_time=get_settings().offers_ignore_closing_time,
        )
    except QuoteNotFoundError as exc:
        raise QuoteNotFound("No quote of this agent with this id") from exc
    except QuoteAlreadyOrderedError as exc:
        raise QuoteAlreadyOrdered.for_order(exc.order_public_id) from exc
    except QuoteExpiredError as exc:
        raise QuoteExpired() from exc
    except MandateNotFoundError as exc:
        raise MandateNotFound() from exc
    except UnknownProductsError as exc:
        raise UnknownProducts.for_codes(exc.codes) from exc
    except CustomerNumberMissingError as exc:
        raise CustomerNumberMissing() from exc
    except ValioAimoError as exc:
        logger.warning("Valio Aimo API unavailable for placing an order: {}", exc)
        raise ValioAimoApiUnavailable() from exc

    await session.commit()
    return OrderResponse.from_order(order)


@router.get(
    "",
    response_model=OrderListResponse,
    summary="List orders",
    description="Most recent first. An agent sees its own orders; a user sees every "
    "order of their buyer organisation.",
)
async def list_orders(
    principal: OrderReader,
    session: ASession,
    status: Annotated[OrderStatus | None, Query(description="Only orders in this status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrderListResponse:
    total, orders = await services.list_orders(
        session,
        organization_id=principal.organization.id,
        agent_id=principal.agent.id if principal.agent else None,
        status=status,
        limit=limit,
        offset=offset,
    )
    return OrderListResponse(total=total, items=[OrderResponse.from_order(o) for o in orders])


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Read an order",
    description="With its status history and, once decided, the approver's note. While "
    "PENDING_APPROVAL, poll again after `checkAgainAfterSeconds`. An agent reads only its "
    "own orders.",
    responses=to_response_error(OrderNotFound),
)
async def get_order(order_id: UUID4, principal: OrderReader, session: ASession) -> OrderResponse:
    try:
        order = await services.get_order(
            session,
            organization_id=principal.organization.id,
            public_id=order_id,
            agent_id=principal.agent.id if principal.agent else None,
        )
    except OrderNotFoundError as exc:
        raise OrderNotFound() from exc
    return OrderResponse.from_order(order)


@router.get(
    "/{order_id}/trail",
    response_model=OrderTrailResponse,
    summary="Read an order's audit trail",
    description="The audit events behind one order, oldest first and whole: those of the "
    "order, its quote and every earlier quote it revised through `previousQuoteId`, plus "
    "the agent's substitute requests for products in those quotes, from the first quote "
    "until the order's latest event. An agent reads only its own orders, and of them only "
    "what it acted in plus human approvals and rejections and automatic placing.",
    tags=["Audit trail"],
    responses=to_response_error(OrderNotFound),
)
async def get_order_trail(
    order_id: UUID4, principal: AuditReader, session: ASession
) -> OrderTrailResponse:
    try:
        entries = await trail.get_order_trail(
            session,
            organization_id=principal.organization.id,
            order_public_id=order_id,
            visible_to_agent_id=principal.agent.id if principal.agent else None,
        )
    except OrderNotFoundError as exc:
        raise OrderNotFound() from exc
    return OrderTrailResponse(
        order_id=order_id, items=[AuditEventOut.from_entry(entry) for entry in entries]
    )


@router.post(
    "/{order_id}/approve",
    response_model=OrderResponse,
    summary="Approve a pending order",
    description="Users only; an Agent token is refused whatever its scopes. Re-checks "
    "live data once more; the NEEDS_HUMAN reasons the order was pending with are what the "
    "approver accepts. A REJECT reason that now applies (e.g. the closing time has passed) "
    "makes it REJECTED with that reason. A NEEDS_HUMAN reason the order wasn't pending "
    "with (e.g. a price rise now over a cap), or a total above the one it was pending "
    "with, keeps it PENDING_APPROVAL, showing the new reasons and total, to be decided "
    "again: an approval never commits more than the approver saw. Otherwise it is "
    "APPROVED and PLACED.",
    responses=to_response_error(OrderNotFound, OrderNotPending, *_RECHECK_ERRORS),
)
async def approve_order(
    order_id: UUID4,
    approver: Approver,
    session: ASession,
    valio_aimo: AValioAimoClient,
    cache: AOfferCache,
    data: DecisionIn | None = None,
) -> OrderResponse:
    try:
        order = await services.approve_order(
            session,
            valio_aimo,
            cache,
            organization_id=approver.organization.id,
            approver=approver,
            public_id=order_id,
            note=data.note if data else None,
            now=datetime.now(UTC),
            ignore_closing_time=get_settings().offers_ignore_closing_time,
        )
    except OrderNotFoundError as exc:
        raise OrderNotFound() from exc
    except OrderNotPendingError as exc:
        raise OrderNotPending(str(exc)) from exc
    except MandateNotFoundError as exc:
        raise MandateNotFound() from exc
    except UnknownProductsError as exc:
        raise UnknownProducts.for_codes(exc.codes) from exc
    except CustomerNumberMissingError as exc:
        raise CustomerNumberMissing() from exc
    except ValioAimoError as exc:
        logger.warning("Valio Aimo API unavailable for approving an order: {}", exc)
        raise ValioAimoApiUnavailable() from exc

    await session.commit()
    return OrderResponse.from_order(order)


@router.post(
    "/{order_id}/reject",
    response_model=OrderResponse,
    summary="Reject a pending order",
    description="Users only; an Agent token is refused whatever its scopes.",
    responses=to_response_error(OrderNotFound, OrderNotPending),
)
async def reject_order(
    order_id: UUID4,
    approver: Approver,
    session: ASession,
    data: DecisionIn | None = None,
) -> OrderResponse:
    try:
        order = await services.reject_order(
            session,
            organization_id=approver.organization.id,
            approver=approver,
            public_id=order_id,
            note=data.note if data else None,
            now=datetime.now(UTC),
        )
    except OrderNotFoundError as exc:
        raise OrderNotFound() from exc
    except OrderNotPendingError as exc:
        raise OrderNotPending(str(exc)) from exc

    await session.commit()
    return OrderResponse.from_order(order)
