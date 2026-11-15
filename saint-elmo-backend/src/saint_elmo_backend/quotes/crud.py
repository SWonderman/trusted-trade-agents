from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from saint_elmo_backend.quotes.models import Quote


async def get_quote(
    session: AsyncSession,
    *,
    organization_id: int,
    public_id: UUID,
    agent_id: int | None = None,
    for_update: bool = False,
) -> Quote | None:
    """
    With its lines and previous quote loaded. `agent_id` limits it to that agent's
    quotes. `for_update` locks the quote row until the transaction ends, so two orders
    placed from it run one after the other.
    """
    stmt = (
        select(Quote)
        .where(Quote.org_id == organization_id, Quote.public_id == public_id)
        .options(selectinload(Quote.lines), joinedload(Quote.previous_quote))
    )
    if agent_id is not None:
        stmt = stmt.where(Quote.agent_id == agent_id)
    if for_update:
        stmt = stmt.with_for_update(of=Quote)
    return await session.scalar(stmt)
