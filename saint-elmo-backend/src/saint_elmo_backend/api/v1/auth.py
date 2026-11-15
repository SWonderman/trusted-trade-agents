"""
Request authentication: resolves the caller to a `Principal` from one of two schemes.

- User sessions: HS256 JWTs signed with `JWT_SECRET`, issued by `POST /api/v1/auth/token`.
- Agent tokens: EdDSA JWTs signed with the agent token key (ADR 0003).

Both arrive as `Authorization: Bearer`. The token's `alg` header picks the scheme, and each
scheme then pins its own algorithm, key and audience, so a token of one scheme can never
pass as the other.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import Annotated

import jwt
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts import services as account_services
from saint_elmo_backend.accounts import tokens as user_session_tokens
from saint_elmo_backend.accounts.dtos import AuthenticatedUser, OrganizationRef
from saint_elmo_backend.accounts.enums import Permission
from saint_elmo_backend.accounts.exceptions import InvalidCredentialsError
from saint_elmo_backend.accounts.permissions import role_has_permission
from saint_elmo_backend.agents import services as agent_services
from saint_elmo_backend.agents import tokens as agent_tokens
from saint_elmo_backend.agents.dtos import AuthenticatedAgent
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.agents.exceptions import InvalidAgentTokenError
from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.api.exceptions import InvalidCredentials, PermissionDenied

user_session_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token",
    scheme_name="UserSession",
    description="A user session issued by `POST /api/v1/auth/token`.",
    auto_error=False,
)

agent_token_scheme = HTTPBearer(
    scheme_name="AgentToken",
    bearerFormat="JWT",
    description=(
        "An Agent token: an EdDSA-signed JWT a buyer admin issues for one agent. Verify it "
        "with the key at `/.well-known/jwks.json`. Each operation lists the scope it requires."
    ),
    auto_error=False,
)


@dataclass(frozen=True, slots=True)
class Principal:
    """
    Who is calling: a user or an agent, always within exactly one buyer organization.

    Services take `organization.id` from here as a required argument (ADR 0004).
    """

    organization: OrganizationRef
    user: AuthenticatedUser | None = None
    agent: AuthenticatedAgent | None = None


async def _resolve_principal(session: AsyncSession, token: str) -> Principal:
    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
    except InvalidTokenError:
        raise InvalidCredentials() from None

    if algorithm == user_session_tokens.ALGORITHM:
        try:
            user = await account_services.authenticate_session(session, token)
        except InvalidCredentialsError:
            raise InvalidCredentials() from None
        return Principal(organization=user.organization, user=user)

    if algorithm == agent_tokens.ALGORITHM:
        try:
            agent = await agent_services.authenticate_agent(session, token)
        except InvalidAgentTokenError:
            raise InvalidCredentials() from None
        # Persist the credential's last use. Authentication is the first work on the
        # request's session, so this commit holds nothing of the route's.
        await session.commit()
        return Principal(organization=agent.organization, agent=agent)

    raise InvalidCredentials()


def authenticate(*, users: bool = False, agent_scope: Scope | None = None):
    """
    Route dependency resolving the caller to a `Principal`.

    `users` admits user sessions; `agent_scope` admits Agent tokens holding that scope.
    No or invalid credentials -> 401 INVALID_CREDENTIALS. A valid credential of a scheme
    the route doesn't accept, or an Agent token without the scope -> 403 PERMISSION_DENIED.
    """

    if not users and agent_scope is None:
        raise ValueError("A route must accept user sessions, Agent tokens, or both")

    async def dependency(
        session: AsyncSession,
        user_session: str | None = None,
        agent_token: HTTPAuthorizationCredentials | None = None,
    ) -> AsyncIterator[Principal]:
        # Both schemes read the same Authorization header
        token = user_session or (agent_token.credentials if agent_token else None)
        if not token:
            raise InvalidCredentials()

        principal = await _resolve_principal(session, token)

        if principal.agent is not None:
            if agent_scope is None:
                raise PermissionDenied("This operation is not available to agents")
            if agent_scope not in principal.agent.scopes:
                raise PermissionDenied(f"The Agent token lacks the `{agent_scope}` scope")
            context = {"agent_public_id": principal.agent.public_id}
        else:
            if not users:
                raise PermissionDenied("This operation is only available to agents")
            assert principal.user is not None
            context = {"user_public_id": principal.user.public_id}

        with logger.contextualize(
            organization_public_id=principal.organization.public_id, **context
        ):
            yield principal

    # Declare only the accepted schemes, so the route's OpenAPI security lists exactly those
    parameters = [Parameter("session", Parameter.KEYWORD_ONLY, annotation=ASession)]
    if users:
        parameters.append(
            Parameter(
                "user_session",
                Parameter.KEYWORD_ONLY,
                annotation=Annotated[str | None, Depends(user_session_scheme)],
            )
        )
    if agent_scope is not None:
        parameters.append(
            Parameter(
                "agent_token",
                Parameter.KEYWORD_ONLY,
                annotation=Annotated[
                    HTTPAuthorizationCredentials | None,
                    Security(agent_token_scheme, scopes=[agent_scope]),
                ],
            )
        )
    dependency.__signature__ = Signature(parameters)  # type: ignore[attr-defined]

    return dependency


async def get_current_user(
    principal: Annotated[Principal, Depends(authenticate(users=True))],
) -> AuthenticatedUser:
    assert principal.user is not None
    return principal.user


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]


def require_permission(*permissions: Permission):
    async def _guard(user: CurrentUser) -> AuthenticatedUser:
        if not all(role_has_permission(user.role, permission) for permission in permissions):
            raise PermissionDenied()

        return user

    return _guard


# A user reads the buyer organisation's audit trail; an agent what it acted in, plus a
# human's decisions on its own orders
AuditReader = Annotated[Principal, Depends(authenticate(users=True, agent_scope=Scope.AUDIT_READ))]
