from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from saint_elmo_backend.orders.enums import OrderStatus
from saint_elmo_backend.orders.models import Order
from saint_elmo_backend.quotes.models import Quote


def _with_details(stmt: Select[tuple[Order]]) -> Select[tuple[Order]]:
    """
    Everything an order response shows: lines, status history, agent and quote.
    """
    return stmt.options(
        selectinload(Order.lines),
        selectinload(Order.status_history),
        joinedload(Order.agent),
        joinedload(Order.quote).selectinload(Quote.lines),
    )


async def get_order(
    session: AsyncSession,
    *,
    organization_id: int,
    public_id: UUID,
    agent_id: int | None = None,
    for_update: bool = False,
) -> Order | None:
    """
    `agent_id` limits it to that agent's orders. `for_update` locks the order row until
    the transaction ends, so two decisions on it run one after the other.
    """
    stmt = select(Order).where(Order.org_id == organization_id, Order.public_id == public_id)
    if agent_id is not None:
        stmt = stmt.where(Order.agent_id == agent_id)
    if for_update:
        stmt = stmt.with_for_update(of=Order)
    return await session.scalar(_with_details(stmt))


async def get_order_for_quote(
    session: AsyncSession, *, organization_id: int, quote_id: int
) -> Order | None:
    return await session.scalar(
        select(Order).where(Order.org_id == organization_id, Order.quote_id == quote_id)
    )


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
    The total matching and one page of them, most recent first.
    """
    stmt = select(Order).where(Order.org_id == organization_id)
    if agent_id is not None:
        stmt = stmt.where(Order.agent_id == agent_id)
    if status is not None:
        stmt = stmt.where(Order.status == status)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    page = await session.scalars(
        _with_details(stmt.order_by(Order.created_at.desc(), Order.id.desc()))
        .limit(limit)
        .offset(offset)
    )
    return total or 0, list(page)
