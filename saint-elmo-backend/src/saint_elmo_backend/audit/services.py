from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.audit.models import AuditEvent


async def record_event(
    session: AsyncSession,
    *,
    organization_id: int,
    event_type: AuditEventType,
    payload: dict[str, Any],
    agent_id: int | None = None,
    user_id: int | None = None,
    subject_public_id: UUID | None = None,
) -> AuditEvent:
    """
    Append one event to the buyer organization's audit trail. `payload` must be
    JSON-serializable.

    A composable building block: the caller owns the commit, so the event lands in the
    same transaction as the change it records.
    """
    event = AuditEvent(
        org_id=organization_id,
        event_type=event_type,
        agent_id=agent_id,
        user_id=user_id,
        subject_public_id=subject_public_id,
        payload=payload,
    )
    session.add(event)
    await session.flush()
    return event
