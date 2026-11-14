from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from saint_elmo_backend.accounts.models import Organization, User


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).options(joinedload(User.organization)).where(User.email == email)
    return await session.scalar(stmt)


async def get_user_by_public_id(session: AsyncSession, public_id: UUID) -> User | None:
    stmt = select(User).options(joinedload(User.organization)).where(User.public_id == public_id)
    return await session.scalar(stmt)


async def get_customer_number(session: AsyncSession, organization_id: int) -> str | None:
    """
    The buyer organisation's Valio Aimo customer number, if it has one.
    """
    stmt = select(Organization.customer_number).where(Organization.id == organization_id)
    return await session.scalar(stmt)
