from typing import Literal

from pydantic import UUID4, BaseModel, EmailStr

from saint_elmo_backend.accounts.dtos import AuthenticatedUser
from saint_elmo_backend.accounts.enums import Role
from saint_elmo_backend.core.schema import CamelBaseModel


class AccessTokenResponse(BaseModel):
    """
    OAuth 2.0 token response (RFC 6749).
    """

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class OrganizationSummary(CamelBaseModel):
    public_id: UUID4
    name: str


class MeOutput(CamelBaseModel):
    public_id: UUID4
    email: EmailStr
    first_name: str
    last_name: str
    role: Role
    organization: OrganizationSummary

    @classmethod
    def from_user(cls, user: AuthenticatedUser) -> "MeOutput":
        return cls(
            public_id=user.public_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            organization=OrganizationSummary(
                public_id=user.organization.public_id,
                name=user.organization.name,
            ),
        )
