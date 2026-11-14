from collections.abc import Collection
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts.services import organization_ref
from saint_elmo_backend.agents import crud, tokens
from saint_elmo_backend.agents.dtos import AuthenticatedAgent, IssuedAgentToken
from saint_elmo_backend.agents.enums import AgentStatus, Scope
from saint_elmo_backend.agents.exceptions import (
    AgentCredentialNotFoundError,
    AgentNotFoundError,
    InvalidAgentTokenError,
)
from saint_elmo_backend.agents.models import Agent, AgentCredential
from saint_elmo_backend.audit import services as audit_services
from saint_elmo_backend.audit.enums import AuditEventType
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


def _token_terms(scopes: Collection[Scope], expires_at: datetime) -> dict[str, Any]:
    return {
        "scopes": sorted(str(scope) for scope in scopes),
        "expiresAt": expires_at.isoformat().replace("+00:00", "Z"),
    }


async def get_agent(session: AsyncSession, *, organization_id: int, public_id: UUID) -> Agent:
    agent = await crud.get_agent_by_public_id(
        session, organization_id=organization_id, public_id=public_id
    )
    if agent is None:
        raise AgentNotFoundError()
    return agent


async def issue_token_for_agent(
    session: AsyncSession,
    *,
    organization_id: int,
    agent_public_id: UUID,
    label: str,
    scopes: Collection[Scope],
    lifetime: timedelta,
    issued_by_user_id: int,
) -> IssuedAgentToken:
    """
    A buyer admin issuing a token for one of their buyer organization's agents.

    The caller owns the commit.
    """

    agent = await get_agent(session, organization_id=organization_id, public_id=agent_public_id)
    issued = await issue_agent_token(
        session,
        agent,
        label=label,
        scopes=scopes,
        lifetime=lifetime,
        created_by_user_id=issued_by_user_id,
    )
    await audit_services.record_event(
        session,
        organization_id=organization_id,
        event_type=AuditEventType.AGENT_TOKEN_ISSUED,
        user_id=issued_by_user_id,
        agent_id=agent.id,
        subject_public_id=agent.public_id,
        payload={
            "jti": str(issued.jti),
            "label": label,
            **_token_terms(scopes, issued.expires_at),
        },
    )
    return issued


async def list_agent_tokens(
    session: AsyncSession, *, organization_id: int, agent_public_id: UUID
) -> list[AgentCredential]:
    """
    The agent's issued tokens, newest first: their credential rows, never a token value.
    """

    agent = await get_agent(session, organization_id=organization_id, public_id=agent_public_id)
    return await crud.list_credentials(session, organization_id=organization_id, agent_id=agent.id)


async def revoke_agent_token(
    session: AsyncSession,
    *,
    organization_id: int,
    agent_public_id: UUID,
    jti: UUID,
    revoked_by_user_id: int,
) -> AgentCredential:
    """
    Revoke one of the agent's tokens, refused from the next request on. Revoking a
    revoked token changes nothing.

    The caller owns the commit.
    """

    agent = await get_agent(session, organization_id=organization_id, public_id=agent_public_id)
    credential = await crud.get_agent_credential(
        session, organization_id=organization_id, agent_id=agent.id, jti=jti
    )
    if credential is None:
        raise AgentCredentialNotFoundError()

    if credential.revoked_at is None:
        credential.revoked_at = datetime.now(UTC)
        await session.flush()
        await audit_services.record_event(
            session,
            organization_id=organization_id,
            event_type=AuditEventType.AGENT_TOKEN_REVOKED,
            user_id=revoked_by_user_id,
            agent_id=agent.id,
            subject_public_id=agent.public_id,
            payload={
                "jti": str(credential.jti),
                **_token_terms(credential.scopes, credential.expires_at),
            },
        )
    return credential


async def disable_agent(
    session: AsyncSession, *, organization_id: int, agent_public_id: UUID, disabled_by_user_id: int
) -> Agent:
    """
    Disable the agent: every one of its tokens is refused from the next request on.
    Disabling a disabled agent changes nothing.

    The caller owns the commit.
    """

    agent = await get_agent(session, organization_id=organization_id, public_id=agent_public_id)
    if agent.status != AgentStatus.DISABLED:
        live = await crud.list_live_credentials(
            session, organization_id=organization_id, agent_id=agent.id, now=datetime.now(UTC)
        )
        agent.status = AgentStatus.DISABLED
        await session.flush()
        await audit_services.record_event(
            session,
            organization_id=organization_id,
            event_type=AuditEventType.AGENT_DISABLED,
            user_id=disabled_by_user_id,
            agent_id=agent.id,
            subject_public_id=agent.public_id,
            payload={"cutOffJtis": [str(credential.jti) for credential in live]},
        )
    return agent


async def list_agents(session: AsyncSession, *, organization_id: int) -> list[Agent]:
    return await crud.list_agents(session, organization_id=organization_id)


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
