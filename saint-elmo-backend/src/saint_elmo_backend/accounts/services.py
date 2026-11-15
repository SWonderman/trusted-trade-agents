from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts import crud, tokens
from saint_elmo_backend.accounts.dtos import AuthenticatedUser, OrganizationRef
from saint_elmo_backend.accounts.exceptions import InvalidCredentialsError
from saint_elmo_backend.accounts.models import Organization, User
from saint_elmo_backend.core.passwords import hash_password, verify_password

_DUMMY_HASH = hash_password("dummy-password-for-constant-time-auth")


def organization_ref(organization: Organization) -> OrganizationRef:
    return OrganizationRef(
        id=organization.id, public_id=organization.public_id, name=organization.name
    )


def _to_authenticated_user(user: User) -> AuthenticatedUser:
    if not user.is_active or not user.organization.is_active:
        raise InvalidCredentialsError()

    return AuthenticatedUser(
        id=user.id,
        public_id=user.public_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        organization=organization_ref(user.organization),
    )


async def authenticate_user(session: AsyncSession, email: str, password: str) -> AuthenticatedUser:
    user = await crud.get_user_by_email(session, email.strip().lower())
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise InvalidCredentialsError()

    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    return _to_authenticated_user(user)


async def authenticate_session(session: AsyncSession, token: str) -> AuthenticatedUser:
    """
    Resolve a user session to the user it names.

    The user must still be active, in an active buyer organization, and in the buyer
    organization the session was issued for.
    """

    claims = tokens.verify(token)

    user = await crud.get_user_by_public_id(session, claims.user_public_id)
    if user is None or user.organization.public_id != claims.organization_public_id:
        raise InvalidCredentialsError()

    return _to_authenticated_user(user)
