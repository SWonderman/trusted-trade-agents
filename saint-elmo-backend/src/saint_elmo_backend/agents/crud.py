from datetime import datetime
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


async def list_agents(session: AsyncSession, *, organization_id: int) -> list[Agent]:
    stmt = select(Agent).where(Agent.org_id == organization_id).order_by(Agent.name)
    return list(await session.scalars(stmt))


async def get_agent_by_public_id(
    session: AsyncSession, *, organization_id: int, public_id: UUID, for_update: bool = False
) -> Agent | None:
    """
    With `for_update`, locks the agent's row until the transaction ends and reads it fresh.
    """

    stmt = (
        select(Agent)
        .options(joinedload(Agent.organization))
        .where(Agent.org_id == organization_id, Agent.public_id == public_id)
    )
    if for_update:
        stmt = stmt.with_for_update(of=Agent).execution_options(populate_existing=True)
    return await session.scalar(stmt)


async def list_credentials(
    session: AsyncSession, *, organization_id: int, agent_id: int
) -> list[AgentCredential]:
    stmt = (
        select(AgentCredential)
        .options(joinedload(AgentCredential.created_by))
        .where(AgentCredential.org_id == organization_id, AgentCredential.agent_id == agent_id)
        .order_by(AgentCredential.created_at.desc(), AgentCredential.id.desc())
    )
    return list(await session.scalars(stmt))


async def get_agent_credential(
    session: AsyncSession, *, organization_id: int, agent_id: int, jti: UUID
) -> AgentCredential | None:
    """
    Locks the credential's row until the transaction ends and reads it fresh.
    """

    stmt = (
        select(AgentCredential)
        .options(joinedload(AgentCredential.created_by))
        .where(
            AgentCredential.org_id == organization_id,
            AgentCredential.agent_id == agent_id,
            AgentCredential.jti == jti,
        )
        .with_for_update(of=AgentCredential)
        .execution_options(populate_existing=True)
    )
    return await session.scalar(stmt)


async def list_live_credentials(
    session: AsyncSession, *, organization_id: int, agent_id: int, now: datetime
) -> list[AgentCredential]:
    """
    The agent's tokens that are neither revoked nor expired.
    """

    stmt = (
        select(AgentCredential)
        .where(
            AgentCredential.org_id == organization_id,
            AgentCredential.agent_id == agent_id,
            AgentCredential.revoked_at.is_(None),
            AgentCredential.expires_at > now,
        )
        .order_by(AgentCredential.created_at, AgentCredential.id)
    )
    return list(await session.scalars(stmt))
