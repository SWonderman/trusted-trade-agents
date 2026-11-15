"""
Reading the audit trail back: the flat event list and one order's trail.

Separate from `services`, which only records events, so that recording (used by orders)
doesn't depend on reading (which uses orders).
"""

import base64
import binascii
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.audit import crud
from saint_elmo_backend.audit.dtos import SYSTEM_ACTOR, ActorRef, AuditEntry, AuditPage
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.audit.exceptions import InvalidCursorError
from saint_elmo_backend.audit.models import AuditEvent
from saint_elmo_backend.audit.summaries import summarize
from saint_elmo_backend.orders import services as order_services
from saint_elmo_backend.quotes.models import Quote


def _encode_cursor(event_id: int) -> str:
    return base64.urlsafe_b64encode(f"before:{event_id}".encode()).decode()


def _decode_cursor(cursor: str) -> int:
    try:
        prefix, _, value = base64.urlsafe_b64decode(cursor.encode()).decode().partition(":")
        if prefix != "before":
            raise ValueError(prefix)
        return int(value)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursorError() from exc


async def list_events(
    session: AsyncSession,
    *,
    organization_id: int,
    visible_to_agent_id: int | None = None,
    agent_public_id: UUID | None = None,
    event_type: AuditEventType | None = None,
    subject_public_id: UUID | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    cursor: str | None = None,
    limit: int,
) -> AuditPage:
    """
    One page of the buyer organisation's events, newest first. `visible_to_agent_id`
    limits it to what that agent may read. Raises `InvalidCursorError`.
    """
    events = await crud.list_events(
        session,
        organization_id=organization_id,
        visible_to_agent_id=visible_to_agent_id,
        agent_public_id=agent_public_id,
        event_type=event_type,
        subject_public_id=subject_public_id,
        since=since,
        until=until,
        before_id=_decode_cursor(cursor) if cursor else None,
        limit=limit + 1,
    )
    page = events[:limit]
    next_cursor = _encode_cursor(page[-1].id) if len(events) > limit else None
    return AuditPage(items=await _entries(session, organization_id, page), next_cursor=next_cursor)


async def get_order_trail(
    session: AsyncSession,
    *,
    organization_id: int,
    order_public_id: UUID,
    visible_to_agent_id: int | None = None,
) -> list[AuditEntry]:
    """
    The events behind one order, oldest first: those about the order, its quote and
    every earlier quote it revised, plus the agent's substitute requests for any product
    in those quotes from the first quote until the order's latest event.

    `visible_to_agent_id` limits it to that agent's own order and what it may read.
    Raises `OrderNotFoundError`.
    """
    order = await order_services.get_order(
        session,
        organization_id=organization_id,
        public_id=order_public_id,
        agent_id=visible_to_agent_id,
    )
    quotes = await _quote_chain(session, organization_id, order.quote)
    events = await crud.list_subject_events(
        session,
        organization_id=organization_id,
        subject_public_ids=[order.public_id, *(quote.public_id for quote in quotes)],
        visible_to_agent_id=visible_to_agent_id,
    )
    product_codes = {line.product_code for quote in quotes for line in quote.lines}
    if events and product_codes:
        # Until substitute requests are linked to quote lines, match them by agent,
        # product and time
        substitute_requests = await crud.list_substitute_requests(
            session,
            organization_id=organization_id,
            agent_id=order.agent_id,
            product_codes=product_codes,
            since=min(quote.created_at for quote in quotes),
            until=max(event.created_at for event in events),
        )
        events = sorted([*events, *substitute_requests], key=lambda event: event.id)
    return await _entries(session, organization_id, events)


async def _quote_chain(session: AsyncSession, organization_id: int, quote: Quote) -> list[Quote]:
    """
    The quote and every earlier quote it revised through `previousQuoteId`, newest
    first, with their lines.
    """
    chain = [quote]
    seen = {quote.id}
    while (previous_id := chain[-1].previous_quote_id) is not None and previous_id not in seen:
        previous = await crud.get_quote_with_lines(
            session, organization_id=organization_id, quote_id=previous_id
        )
        if previous is None:
            break
        seen.add(previous.id)
        chain.append(previous)
    return chain


async def _entries(
    session: AsyncSession, organization_id: int, events: list[AuditEvent]
) -> list[AuditEntry]:
    agents = await crud.agent_names(
        session,
        organization_id=organization_id,
        ids={event.agent_id for event in events if event.agent_id is not None},
    )
    users = await crud.user_names(
        session,
        organization_id=organization_id,
        ids={event.user_id for event in events if event.user_id is not None},
    )

    def actor(event: AuditEvent) -> ActorRef:
        # A buyer admin's action on an agent carries both: the user acted
        if event.user_id is not None:
            public_id, name = users[event.user_id]
            return ActorRef(kind="user", public_id=public_id, name=name)
        if event.agent_id is not None:
            public_id, name = agents[event.agent_id]
            return ActorRef(kind="agent", public_id=public_id, name=name)
        return SYSTEM_ACTOR

    entries = []
    for event in events:
        who = actor(event)
        about = agents[event.agent_id][1] if event.agent_id is not None else None
        entries.append(
            AuditEntry(
                event=event,
                actor=who,
                summary=summarize(event.event_type, event.payload, actor=who.name, agent=about),
            )
        )
    return entries
