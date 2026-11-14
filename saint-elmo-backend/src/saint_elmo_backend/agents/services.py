from collections.abc import Collection
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts.services import organization_ref
from saint_elmo_backend.agents import crud, tokens
from saint_elmo_backend.agents.dtos import AuthenticatedAgent, IssuedAgentToken
from saint_elmo_backend.agents.enums import AgentStatus, Scope
from saint_elmo_backend.agents.exceptions import InvalidAgentTokenError
from saint_elmo_backend.agents.models import Agent, AgentCredential
from saint_elmo_backend.mandates import crud as mandate_crud
from saint_elmo_backend.mandates.exceptions import MandateNotFoundError


async def issue_agent_token(
    session: AsyncSession,
    agent: Agent,
    *,
    label: str,
    scopes: Collection[Scope],
    lifetime: timedelta,
    created_by_user_id: int,
) -> IssuedAgentToken:
    """
    Sign an Agent token for `agent`, naming its mandate, and record its credential row,
    issued by the buyer admin `created_by_user_id`.

    A composable building block: the caller owns the commit.
    """

    mandate = await mandate_crud.get_mandate_for_agent(
        session, organization_id=agent.org_id, agent_id=agent.id
    )
    if mandate is None:
        raise MandateNotFoundError()

    now = datetime.now(UTC)
    jti = uuid4()
    expires_at = now + lifetime

    session.add(
        AgentCredential(
            jti=jti,
            label=label,
            scopes=sorted(scopes),
            expires_at=expires_at,
            agent_id=agent.id,
            org_id=agent.org_id,
            created_by_user_id=created_by_user_id,
        )
    )
    await session.flush()

    token = tokens.sign(
        jti=jti,
        agent_public_id=agent.public_id,
        organization_public_id=agent.organization.public_id,
        mandate_public_id=mandate.public_id,
        scopes=scopes,
        issued_at=now,
        expires_at=expires_at,
    )
    return IssuedAgentToken(token=token, jti=jti, expires_at=expires_at)


async def authenticate_agent(session: AsyncSession, token: str) -> AuthenticatedAgent:
    """
    Resolve an Agent token to its agent, checking on every request that its credential
    is not revoked, still grants the scopes the token names, and that the agent and its
    buyer organization are still active.

    Records the credential's last use; the caller owns the commit.
    """

    claims = tokens.verify(token)

    credential = await crud.get_credential_by_jti(session, claims.jti)
    if credential is None or credential.revoked_at is not None:
        raise InvalidAgentTokenError()

    agent = credential.agent
    if (
        agent.public_id != claims.agent_public_id
        or agent.organization.public_id != claims.organization_public_id
        or frozenset(credential.scopes) != claims.scopes
        or agent.status != AgentStatus.ACTIVE
        or not agent.organization.is_active
    ):
        raise InvalidAgentTokenError()

    credential.last_used_at = datetime.now(UTC)
    await session.flush()

    return AuthenticatedAgent(
        id=agent.id,
        public_id=agent.public_id,
        name=agent.name,
        organization=organization_ref(agent.organization),
        mandate_public_id=claims.mandate_public_id,
        scopes=claims.scopes,
        credential_jti=credential.jti,
    )
