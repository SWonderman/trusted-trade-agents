from dataclasses import dataclass
from uuid import UUID

from saint_elmo_backend.accounts.enums import Role


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
    org_id: int
    organization_public_id: UUID
    organization_name: str
