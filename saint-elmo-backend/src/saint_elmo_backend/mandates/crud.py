from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.mandates.models import Mandate

# Period spend is counted from the order book's tables; nothing else of orders is used
from saint_elmo_backend.orders.enums import COMMITTING_STATUSES
from saint_elmo_backend.orders.models import Order, OrderLine


async def get_mandate_for_agent(
    session: AsyncSession, *, organization_id: int, agent_id: int
) -> Mandate | None:
    stmt = select(Mandate).where(Mandate.org_id == organization_id, Mandate.agent_id == agent_id)
    return await session.scalar(stmt)


async def committed_spend(
    session: AsyncSession,
    *,
    organization_id: int,
    agent_id: int,
    start: datetime,
    end: datetime,
    excluding_order_id: int | None = None,
) -> tuple[Decimal, dict[str, Decimal]]:
    """
    Net EUR the agent's pending, approved and placed orders created in [start, end)
    commit, in total and per category code.
    """
    stmt = (
        select(OrderLine.category_code, func.sum(OrderLine.net_total))
        .join(Order, OrderLine.order_id == Order.id)
        .where(
            Order.org_id == organization_id,
            Order.agent_id == agent_id,
            Order.status.in_(COMMITTING_STATUSES),
            Order.created_at >= start,
            Order.created_at < end,
            OrderLine.net_total.is_not(None),
        )
        .group_by(OrderLine.category_code)
    )
    if excluding_order_id is not None:
        stmt = stmt.where(Order.id != excluding_order_id)

    by_category = {category: total for category, total in (await session.execute(stmt)).all()}
    return sum(by_category.values(), Decimal(0)), by_category
