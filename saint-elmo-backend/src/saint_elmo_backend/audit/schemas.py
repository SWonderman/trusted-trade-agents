from datetime import datetime
from typing import Any, Literal

from pydantic import UUID4, Field

from saint_elmo_backend.audit.dtos import AuditEntry
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.core.schema import CamelBaseModel
from saint_elmo_backend.policy.enums import PolicyOutcome


class ActorOut(CamelBaseModel):
    kind: Literal["agent", "user", "system"] = Field(
        description='"system" for automatic steps, e.g. placing a confirmed or approved order'
    )
    id: UUID4 | None = Field(description="The agent's or user's id; null for the system")
    name: str = Field(examples=["dairy-restock"])


class AuditEventOut(CamelBaseModel):
    id: UUID4
    at: datetime
    type: AuditEventType
    subject_id: UUID4 | None = Field(
        description="What the event is about: the quote, order or agent. Null for a "
        "substitute request"
    )
    actor: ActorOut = Field(
        description="Who acted. A re-check is credited to whoever triggered it: the agent "
        "when placing, the approver when approving"
    )
    summary: str = Field(
        description="One plain English sentence, rendered when read",
        examples=[
            "dairy-restock quoted 50 KI of 463038 for €1,565.50: needs a human "
            "(over the auto-approve limit)"
        ],
    )
    outcome: PolicyOutcome | None = Field(
        description="The policy outcome, for events that judged against the mandate"
    )
    reason_codes: list[str] | None = Field(
        description="The policy reason codes, for events that judged against the mandate"
    )
    payload: dict[str, Any] = Field(description="The event's recorded data, unchanged")

    @classmethod
    def from_entry(cls, entry: AuditEntry) -> "AuditEventOut":
        event = entry.event
        policy = event.payload.get("policy")
        policy = policy if isinstance(policy, dict) else {}
        reasons = policy.get("reasons")
        return cls(
            id=event.public_id,
            at=event.created_at,
            type=event.event_type,
            subject_id=event.subject_public_id,
            actor=ActorOut(kind=entry.actor.kind, id=entry.actor.public_id, name=entry.actor.name),
            summary=entry.summary,
            outcome=policy.get("outcome"),
            reason_codes=[reason["code"] for reason in reasons] if reasons is not None else None,
            payload=event.payload,
        )


class AuditEventListResponse(CamelBaseModel):
    items: list[AuditEventOut] = Field(description="Newest first")
    next_cursor: str | None = Field(
        description="Pass as `cursor` for the next, older page; null on the last page"
    )


class OrderTrailResponse(CamelBaseModel):
    order_id: UUID4
    items: list[AuditEventOut] = Field(description="Oldest first")
