from dataclasses import dataclass
from uuid import UUID

from saint_elmo_backend.accounts.enums import Role


@dataclass(frozen=True, slots=True)
class OrganizationRef:
    """
    The buyer organization a user or agent acts for.
    """

    id: int
    public_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class UserSessionClaims:
    """
    Fields lifted from a user session whose signature, audience, issuer and expiry are valid.
    """

    user_public_id: UUID
    organization_public_id: UUID


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """
    An active user of an active buyer organization, resolved from credentials or a session.
    """

    id: int
    public_id: UUID
    email: str
    first_name: str
    last_name: str
    role: Role
    organization: OrganizationRef
