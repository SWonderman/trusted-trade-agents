from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from saint_elmo_backend.audit.models import AuditEvent

type ActorKind = Literal["agent", "user", "system"]


@dataclass(frozen=True, slots=True)
class ActorRef:
    """
    Who an event is credited to. "system" for automatic steps, e.g. placing a confirmed order.
    """

    kind: ActorKind
    public_id: UUID | None
    name: str


SYSTEM_ACTOR = ActorRef(kind="system", public_id=None, name="system")


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """
    One audit event as read back: the stored row, who acted, and its sentence.
    """

    event: AuditEvent
    actor: ActorRef
    summary: str


@dataclass(frozen=True, slots=True)
class AuditPage:
    items: list[AuditEntry]
    # Pass back to get the next, older page; None on the last
    next_cursor: str | None
