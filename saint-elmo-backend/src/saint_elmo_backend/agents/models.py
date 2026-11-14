import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saint_elmo_backend.accounts.models import Organization
from saint_elmo_backend.agents.enums import AgentStatus, Scope
from saint_elmo_backend.db.base import Base
from saint_elmo_backend.db.mixins import OrgOwnedMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from saint_elmo_backend.mandates.models import Mandate


class Agent(Base, PublicIdMixin, TimestampMixin, OrgOwnedMixin):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status"), default=AgentStatus.ACTIVE
    )

    organization: Mapped[Organization] = relationship()
    credentials: Mapped[list["AgentCredential"]] = relationship(back_populates="agent")
    mandate: Mapped["Mandate | None"] = relationship(back_populates="agent")


class AgentCredential(Base, TimestampMixin, OrgOwnedMixin):
    """
    One issued Agent token. The token itself is never stored, only its `jti`, which every
    request looks up so that revocation takes effect on the next request.
    """

    __tablename__ = "agent_credentials"

    jti: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), unique=True)
    label: Mapped[str] = mapped_column(String(255))
    # Stored as the scope strings themselves ("catalog:read"), the same as in the token
    scopes: Mapped[list[Scope]] = mapped_column(
        ARRAY(
            Enum(
                Scope,
                native_enum=False,
                length=32,
                values_callable=lambda scopes: [scope.value for scope in scopes],
            )
        )
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    agent: Mapped[Agent] = relationship(back_populates="credentials")

    # The buyer admin who issued the token. RESTRICT: users are deactivated, never
    # deleted, so who granted an agent its authority stays on record
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
