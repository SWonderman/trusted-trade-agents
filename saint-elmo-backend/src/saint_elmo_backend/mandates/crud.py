from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.mandates.models import Mandate


async def get_mandate_for_agent(
    session: AsyncSession, *, organization_id: int, agent_id: int
) -> Mandate | None:
    stmt = select(Mandate).where(Mandate.org_id == organization_id, Mandate.agent_id == agent_id)
    return await session.scalar(stmt)
