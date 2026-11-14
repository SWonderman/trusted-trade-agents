import uuid
from typing import Any

from sqlalchemy import Enum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.db import annotations
from saint_elmo_backend.db.base import Base
from saint_elmo_backend.db.mixins import OrgOwnedMixin, PublicIdMixin
from saint_elmo_backend.db.types import JSONB_


class AuditEvent(Base, PublicIdMixin, OrgOwnedMixin):
    """
    One entry of the audit trail: who did what, when, and with what data. Append-only:
    rows are inserted through `services.record_event` and never changed.
    """

    __tablename__ = "audit_events"

    created_at: Mapped[annotations.created_at] = mapped_column()
    event_type: Mapped[AuditEventType] = mapped_column(
        Enum(AuditEventType, name="audit_event_type")
    )
    # The actor: an agent or a user
    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("agents.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    # Public id of what the event is about, e.g. the quote
    subject_public_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    # camelCase JSON, as in the API
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB_)
