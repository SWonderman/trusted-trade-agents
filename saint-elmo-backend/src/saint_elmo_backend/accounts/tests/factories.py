"""
Insert buyer organizations and users for integration tests, and mint user sessions.

Users are seeded, never signed up, so tests arrange them directly in the database.
"""

from itertools import count

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts import tokens
from saint_elmo_backend.accounts.dtos import AuthenticatedUser
from saint_elmo_backend.accounts.enums import Role
from saint_elmo_backend.accounts.models import Organization, User
from saint_elmo_backend.accounts.services import organization_ref
from saint_elmo_backend.core.passwords import hash_password

DEFAULT_PASSWORD = "correct-horse-battery-staple"

_numbers = count(1)


async def make_organization(
    session: AsyncSession,
    *,
    name: str | None = None,
    is_active: bool = True,
) -> Organization:
    number = next(_numbers)
    organization = Organization(
        name=name or f"Buyer organisation {number}",
        customer_number=f"C{number:06d}",
        is_active=is_active,
    )
    session.add(organization)
    await session.flush()
    return organization


async def make_user(
    session: AsyncSession,
    organization: Organization,
    *,
    email: str | None = None,
    password: str = DEFAULT_PASSWORD,
    role: Role = Role.BUYER_ADMIN,
    is_active: bool = True,
) -> User:
    number = next(_numbers)
    user = User(
        first_name="Ada",
        last_name=f"Buyer {number}",
        email=(email or f"user{number}@example.com").lower(),
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
        organization=organization,
    )
    session.add(user)
    await session.flush()
    return user


def user_session_headers(user: User) -> dict[str, str]:
    """
    `Authorization` header with a valid user session for `user`, without going through login.
    """

    token, _ = tokens.sign(
        AuthenticatedUser(
            id=user.id,
            public_id=user.public_id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            organization=organization_ref(user.organization),
        )
    )
    return {"Authorization": f"Bearer {token}"}
