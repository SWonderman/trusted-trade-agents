"""
Insert agents for integration tests and issue their Agent tokens.

Tokens go through the real issuance service, so tests exercise issuance and
verification together.
"""

from collections.abc import Collection
from datetime import timedelta
from itertools import count
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts.models import Organization
from saint_elmo_backend.accounts.tests.factories import make_user
from saint_elmo_backend.agents import services
from saint_elmo_backend.agents.dtos import IssuedAgentToken
from saint_elmo_backend.agents.enums import AgentStatus, Scope
from saint_elmo_backend.agents.models import Agent

_numbers = count(1)


async def make_agent(
    session: AsyncSession,
    organization: Organization,
    *,
    name: str | None = None,
    status: AgentStatus = AgentStatus.ACTIVE,
) -> Agent:
    agent = Agent(
        name=name or f"agent-{next(_numbers)}",
        status=status,
        organization=organization,
    )
    session.add(agent)
    await session.flush()
    return agent


async def issue_token(
    session: AsyncSession,
    agent: Agent,
    *,
    scopes: Collection[Scope] = tuple(Scope),
    lifetime: timedelta = timedelta(days=7),
) -> IssuedAgentToken:
    """
    Issued by a new buyer admin of the agent's buyer organisation.
    """

    issuer = await make_user(session, agent.organization)
    return await services.issue_agent_token(
        session,
        agent,
        label="test token",
        scopes=scopes,
        lifetime=lifetime,
        mandate_public_id=uuid4(),
        created_by_user_id=issuer.id,
    )


def bearer(token: IssuedAgentToken | str) -> dict[str, str]:
    value = token.token if isinstance(token, IssuedAgentToken) else token
    return {"Authorization": f"Bearer {value}"}
