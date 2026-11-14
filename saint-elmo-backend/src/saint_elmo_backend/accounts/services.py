from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts import crud
from saint_elmo_backend.accounts.dtos import AuthenticatedUser
from saint_elmo_backend.accounts.exceptions import InvalidCredentialsError
from saint_elmo_backend.accounts.models import User
from saint_elmo_backend.core.passwords import hash_password, verify_password

_DUMMY_HASH = hash_password("dummy-password-for-constant-time-auth")


def _to_authenticated_user(user: User) -> AuthenticatedUser | None:
    if not user.is_active or not user.organization.is_active:
        return None

    return AuthenticatedUser(
        id=user.id,
        public_id=user.public_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        org_id=user.org_id,
        organization_public_id=user.organization.public_id,
        organization_name=user.organization.name,
    )


async def authenticate_user(session: AsyncSession, email: str, password: str) -> AuthenticatedUser:
    user = await crud.get_user_by_email(session, email.strip().lower())
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise InvalidCredentialsError()

    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()

    authenticated = _to_authenticated_user(user)
    if authenticated is None:
        raise InvalidCredentialsError()

    return authenticated


async def get_session_user(
    session: AsyncSession, user_public_id: UUID, organization_public_id: UUID
) -> AuthenticatedUser | None:
    """
    Resolve a user session to the user it names. None -> reject.

    The user must still be active, in an active buyer organization, and in the
    buyer organization the session was issued for.
    """

    user = await crud.get_user_by_public_id(session, user_public_id)
    if user is None or user.organization.public_id != organization_public_id:
        return None

    return _to_authenticated_user(user)
