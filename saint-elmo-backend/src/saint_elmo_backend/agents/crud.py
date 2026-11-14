from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from saint_elmo_backend.agents.models import Agent, AgentCredential


async def get_credential_by_jti(session: AsyncSession, jti: UUID) -> AgentCredential | None:
    stmt = (
        select(AgentCredential)
        .options(joinedload(AgentCredential.agent).joinedload(Agent.organization))
        .where(AgentCredential.jti == jti)
    )
    return await session.scalar(stmt)
