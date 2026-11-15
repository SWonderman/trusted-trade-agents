from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from saint_elmo_backend.accounts.models import User
from saint_elmo_backend.agents.models import Agent
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.audit.models import AuditEvent
from saint_elmo_backend.orders.models import Order
from saint_elmo_backend.quotes.models import Quote

# A human's decision on an agent's order, which that agent may read
_HUMAN_DECISIONS = (AuditEventType.ORDER_APPROVED, AuditEventType.ORDER_REJECTED_BY_HUMAN)


def _acted_by_agent(agent_id: int) -> ColumnElement[bool]:
    """
    The agent itself acted. A buyer admin's action on the agent also carries its
    `agent_id`, but is credited to the admin's `user_id`.
    """
    return and_(AuditEvent.agent_id == agent_id, AuditEvent.user_id.is_(None))


def visible_to_agent(organization_id: int, agent_id: int) -> ColumnElement[bool]:
    """
    What an agent may read: the events it acted in, plus a human's approval or rejection
    of its own orders and the system's automatic steps on them (placing).
    """
    own_orders = select(Order.public_id).where(
        Order.org_id == organization_id, Order.agent_id == agent_id
    )
    return or_(
        _acted_by_agent(agent_id),
        and_(
            AuditEvent.subject_public_id.in_(own_orders),
            or_(
                AuditEvent.event_type.in_(_HUMAN_DECISIONS),
                and_(AuditEvent.agent_id.is_(None), AuditEvent.user_id.is_(None)),
            ),
        ),
    )


def _in_organization(organization_id: int, visible_to_agent_id: int | None) -> Select:
    stmt = select(AuditEvent).where(AuditEvent.org_id == organization_id)
    if visible_to_agent_id is not None:
        stmt = stmt.where(visible_to_agent(organization_id, visible_to_agent_id))
    return stmt


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
    before_id: int | None = None,
    limit: int,
) -> list[AuditEvent]:
    """
    Newest first, at most `limit`, those with an id below `before_id` (the cursor).
    `agent_public_id` matches the events carrying that agent, as actor or as subject of
    a buyer admin's action. `since` is inclusive, `until` exclusive.
    """
    stmt = _in_organization(organization_id, visible_to_agent_id)
    if agent_public_id is not None:
        stmt = stmt.where(
            AuditEvent.agent_id
            == select(Agent.id)
            .where(Agent.org_id == organization_id, Agent.public_id == agent_public_id)
            .scalar_subquery()
        )
    if event_type is not None:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if subject_public_id is not None:
        stmt = stmt.where(AuditEvent.subject_public_id == subject_public_id)
    if since is not None:
        stmt = stmt.where(AuditEvent.created_at >= since)
    if until is not None:
        stmt = stmt.where(AuditEvent.created_at < until)
    if before_id is not None:
        stmt = stmt.where(AuditEvent.id < before_id)
    # Ids follow insertion, so they order events recorded in one transaction too
    return list(await session.scalars(stmt.order_by(AuditEvent.id.desc()).limit(limit)))


async def list_subject_events(
    session: AsyncSession,
    *,
    organization_id: int,
    subject_public_ids: list[UUID],
    visible_to_agent_id: int | None = None,
) -> list[AuditEvent]:
    """
    Every event about any of the subjects, oldest first.
    """
    stmt = _in_organization(organization_id, visible_to_agent_id).where(
        AuditEvent.subject_public_id.in_(subject_public_ids)
    )
    return list(await session.scalars(stmt.order_by(AuditEvent.id)))


async def list_substitute_requests(
    session: AsyncSession,
    *,
    organization_id: int,
    agent_id: int,
    product_codes: set[str],
    since: datetime,
    until: datetime,
) -> list[AuditEvent]:
    """
    The agent's SUBSTITUTES_REQUESTED events for any of the product codes, recorded from
    `since` to `until` inclusive, oldest first.
    """
    stmt = select(AuditEvent).where(
        AuditEvent.org_id == organization_id,
        AuditEvent.event_type == AuditEventType.SUBSTITUTES_REQUESTED,
        _acted_by_agent(agent_id),
        AuditEvent.payload["productCode"].as_string().in_(product_codes),
        AuditEvent.created_at >= since,
        AuditEvent.created_at <= until,
    )
    return list(await session.scalars(stmt.order_by(AuditEvent.id)))


async def get_quote_with_lines(
    session: AsyncSession, *, organization_id: int, quote_id: int
) -> Quote | None:
    return await session.scalar(
        select(Quote)
        .options(selectinload(Quote.lines))
        .where(Quote.org_id == organization_id, Quote.id == quote_id)
    )


async def agent_names(
    session: AsyncSession, *, organization_id: int, ids: set[int]
) -> dict[int, tuple[UUID, str]]:
    if not ids:
        return {}
    rows = await session.execute(
        select(Agent.id, Agent.public_id, Agent.name).where(
            Agent.org_id == organization_id, Agent.id.in_(ids)
        )
    )
    return {row.id: (row.public_id, row.name) for row in rows}


async def user_names(
    session: AsyncSession, *, organization_id: int, ids: set[int]
) -> dict[int, tuple[UUID, str]]:
    if not ids:
        return {}
    rows = await session.execute(
        select(User.id, User.public_id, func.concat(User.first_name, " ", User.last_name)).where(
            User.org_id == organization_id, User.id.in_(ids)
        )
    )
    return {row[0]: (row[1], row[2]) for row in rows}
