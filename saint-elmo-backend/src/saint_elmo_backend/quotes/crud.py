from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from saint_elmo_backend.quotes.models import Quote


async def get_quote(
    session: AsyncSession, *, organization_id: int, public_id: UUID
) -> Quote | None:
    """
    With its lines and previous quote loaded.
    """
    stmt = (
        select(Quote)
        .where(Quote.org_id == organization_id, Quote.public_id == public_id)
        .options(selectinload(Quote.lines), joinedload(Quote.previous_quote))
    )
    return await session.scalar(stmt)
