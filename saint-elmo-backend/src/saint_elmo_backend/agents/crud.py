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


async def get_agent_by_name(
    session: AsyncSession, *, organization_id: int, name: str
) -> Agent | None:
    stmt = (
        select(Agent)
        .options(joinedload(Agent.organization))
        .where(Agent.org_id == organization_id, Agent.name == name)
    )
    return await session.scalar(stmt)


async def get_agent(session: AsyncSession, *, organization_id: int, agent_id: int) -> Agent | None:
    stmt = select(Agent).where(Agent.org_id == organization_id, Agent.id == agent_id)
    return await session.scalar(stmt)
