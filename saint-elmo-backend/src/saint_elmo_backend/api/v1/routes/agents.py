from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import UUID4

from saint_elmo_backend.accounts.dtos import AuthenticatedUser
from saint_elmo_backend.accounts.enums import Permission
from saint_elmo_backend.agents import services as agent_services
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.agents.exceptions import AgentCredentialNotFoundError, AgentNotFoundError
from saint_elmo_backend.agents.schemas import (
    AgentListResponse,
    AgentResponse,
    AgentTokenIn,
    AgentTokenListResponse,
    AgentTokenResponse,
    IssuedAgentTokenResponse,
)
from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.api.exceptions import (
    AgentNotFound,
    AgentTokenNotFound,
    InvalidCredentials,
    MandateNotFound,
    MandateRequired,
    PermissionDenied,
    to_response_error,
)
from saint_elmo_backend.api.v1.auth import Principal, authenticate, require_permission
from saint_elmo_backend.mandates import services as mandate_services
from saint_elmo_backend.mandates.exceptions import MandateNotFoundError
from saint_elmo_backend.mandates.schemas import MandateResponse

router = APIRouter()

# Users only: Agent tokens are refused, whatever their scopes, and only buyer admins
# hold AGENT_MANAGE
BuyerAdmin = Annotated[AuthenticatedUser, Depends(require_permission(Permission.AGENT_MANAGE))]


@router.get(
    "/me/mandate",
    response_model=MandateResponse,
    responses=to_response_error(InvalidCredentials, PermissionDenied, MandateNotFound),
    summary="Read the calling agent's mandate",
    description="Every limit Saint Elmo applies to this agent's quotes and orders, and "
    "how much of the current spend period is left. Use it to pre-check a proposal before "
    "quoting. The mandate is the one the Agent token's agent holds now; an agent can read "
    "it but never change it.",
)
async def get_my_mandate(
    principal: Annotated[Principal, Depends(authenticate(agent_scope=Scope.MANDATE_READ))],
    session: ASession,
) -> MandateResponse:
    assert principal.agent is not None
    try:
        mandate = await mandate_services.get_agent_mandate(
            session, organization_id=principal.organization.id, agent_id=principal.agent.id
        )
    except MandateNotFoundError as exc:
        raise MandateNotFound() from exc
    return MandateResponse.from_mandate(principal.agent, mandate)


@router.get(
    "",
    response_model=AgentListResponse,
    responses=to_response_error(InvalidCredentials, PermissionDenied),
    summary="List the buyer organisation's agents",
    description="Buyer admins only; an Agent token is refused whatever its scopes.",
)
async def list_agents(admin: BuyerAdmin, session: ASession) -> AgentListResponse:
    agents = await agent_services.list_agents(session, organization_id=admin.organization.id)
    return AgentListResponse(items=[AgentResponse.from_agent(agent) for agent in agents])


@router.post(
    "/{agent_id}/tokens",
    status_code=status.HTTP_201_CREATED,
    response_model=IssuedAgentTokenResponse,
    responses=to_response_error(
        InvalidCredentials, PermissionDenied, AgentNotFound, MandateRequired
    ),
    summary="Issue an Agent token",
    description="Buyer admins only. Signs a token for the agent naming its mandate, with "
    "`scopes` or a `preset`, expiring after `expiresInDays` (default 7, at most 30). The "
    "token is returned only in this response and never stored: copy it now. It works "
    "from the next request.",
)
async def issue_token(
    agent_id: UUID4, data: AgentTokenIn, admin: BuyerAdmin, session: ASession
) -> IssuedAgentTokenResponse:
    scopes = data.granted_scopes
    try:
        issued = await agent_services.issue_token_as_buyer_admin(
            session,
            organization_id=admin.organization.id,
            agent_public_id=agent_id,
            label=data.label,
            scopes=scopes,
            lifetime=timedelta(days=data.expires_in_days),
            issued_by_user_id=admin.id,
        )
    except AgentNotFoundError as exc:
        raise AgentNotFound() from exc
    except MandateNotFoundError as exc:
        raise MandateRequired() from exc

    await session.commit()
    return IssuedAgentTokenResponse(
        token=issued.token, jti=issued.jti, scopes=sorted(scopes), expires_at=issued.expires_at
    )


@router.get(
    "/{agent_id}/tokens",
    response_model=AgentTokenListResponse,
    responses=to_response_error(InvalidCredentials, PermissionDenied, AgentNotFound),
    summary="List an agent's Agent tokens",
    description="Buyer admins only. Every token issued for the agent, revoked and expired "
    "ones included, with when it was last used. Token values are never shown again.",
)
async def list_agent_tokens(
    agent_id: UUID4, admin: BuyerAdmin, session: ASession
) -> AgentTokenListResponse:
    try:
        credentials = await agent_services.list_agent_tokens(
            session, organization_id=admin.organization.id, agent_public_id=agent_id
        )
    except AgentNotFoundError as exc:
        raise AgentNotFound() from exc
    return AgentTokenListResponse(
        items=[AgentTokenResponse.from_credential(credential) for credential in credentials]
    )


@router.delete(
    "/{agent_id}/tokens/{jti}",
    response_model=AgentTokenResponse,
    responses=to_response_error(
        InvalidCredentials, PermissionDenied, AgentNotFound, AgentTokenNotFound
    ),
    summary="Revoke an Agent token",
    description="Buyer admins only. The token is refused from the very next request. "
    "Revoking a revoked token succeeds and keeps the first revocation time.",
)
async def revoke_agent_token(
    agent_id: UUID4, jti: UUID4, admin: BuyerAdmin, session: ASession
) -> AgentTokenResponse:
    try:
        credential = await agent_services.revoke_agent_token(
            session,
            organization_id=admin.organization.id,
            agent_public_id=agent_id,
            jti=jti,
            revoked_by_user_id=admin.id,
        )
    except AgentNotFoundError as exc:
        raise AgentNotFound() from exc
    except AgentCredentialNotFoundError as exc:
        raise AgentTokenNotFound() from exc

    await session.commit()
    return AgentTokenResponse.from_credential(credential)


@router.post(
    "/{agent_id}/disable",
    response_model=AgentResponse,
    responses=to_response_error(InvalidCredentials, PermissionDenied, AgentNotFound),
    summary="Disable an agent",
    description="Buyer admins only. Every token of the agent is refused from the very "
    "next request. Disabling a disabled agent succeeds and changes nothing.",
)
async def disable_agent(agent_id: UUID4, admin: BuyerAdmin, session: ASession) -> AgentResponse:
    try:
        agent = await agent_services.disable_agent(
            session,
            organization_id=admin.organization.id,
            agent_public_id=agent_id,
            disabled_by_user_id=admin.id,
        )
    except AgentNotFoundError as exc:
        raise AgentNotFound() from exc

    await session.commit()
    return AgentResponse.from_agent(agent)
