from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saint_elmo_backend.accounts.enums import Role
from saint_elmo_backend.db.base import Base
from saint_elmo_backend.db.mixins import OrgOwnedMixin, PublicIdMixin, TimestampMixin


class Organization(Base, PublicIdMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255))
    customer_number: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        comment="Valio Aimo customer number, passed to the mock API",
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base, PublicIdMixin, TimestampMixin, OrgOwnedMixin):
    """
    A human in one buyer organization. Users are seeded; the only account feature is login.
    """

    __tablename__ = "users"

    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="role"))
    is_active: Mapped[bool] = mapped_column(default=True)

    organization: Mapped[Organization] = relationship(back_populates="users")
