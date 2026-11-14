from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saint_elmo_backend.agents.enums import Scope


@dataclass(frozen=True, slots=True)
class AgentTokenClaims:
    """
    Fields lifted from an Agent token whose signature, audience, issuer and expiry are valid.
    """

    jti: UUID
    agent_public_id: UUID
    organization_public_id: UUID
    mandate_public_id: UUID


@dataclass(frozen=True, slots=True)
class AuthenticatedAgent:
    """
    An active agent of an active buyer organization, resolved from an Agent token.
    """

    id: int
    public_id: UUID
    name: str
    org_id: int
    organization_public_id: UUID
    mandate_public_id: UUID
    scopes: frozenset[Scope]
    credential_jti: UUID


@dataclass(frozen=True, slots=True)
class IssuedAgentToken:
    """
    A freshly signed Agent token. `token` is shown once and never stored.
    """

    token: str
    jti: UUID
    expires_at: datetime
