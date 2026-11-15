from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import UUID4

from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.api.annotations import ASession
from saint_elmo_backend.api.exceptions import (
    InvalidCredentials,
    InvalidCursor,
    PermissionDenied,
    to_response_error,
)
from saint_elmo_backend.api.v1.auth import Principal, authenticate
from saint_elmo_backend.audit import trail
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.audit.exceptions import InvalidCursorError
from saint_elmo_backend.audit.schemas import AuditEventListResponse, AuditEventOut

router = APIRouter(responses=to_response_error(InvalidCredentials, PermissionDenied))

# A user reads the buyer organisation's trail; an agent what it acted in, plus a human's
# decisions on its own orders
AuditReader = Annotated[Principal, Depends(authenticate(users=True, agent_scope=Scope.AUDIT_READ))]


@router.get(
    "",
    response_model=AuditEventListResponse,
    summary="List audit events",
    description="The audit trail of decisions and commitments: quotes, substitute "
    "requests, orders, approvals and changes to agents' authority. Lookups such as "
    "searches and price checks are not in it. Newest first; follow `nextCursor` for older "
    "events. A user sees the whole buyer organisation; an agent sees the events it acted "
    "in, plus human approvals and rejections and automatic placing of its own orders.",
    responses=to_response_error(InvalidCursor),
)
async def list_audit_events(
    principal: AuditReader,
    session: ASession,
    agent_id: Annotated[
        UUID4 | None,
        Query(alias="agentId", description="Only events of this agent, as actor or subject"),
    ] = None,
    type: Annotated[AuditEventType | None, Query(description="Only this event type")] = None,
    subject: Annotated[
        UUID4 | None, Query(description="Only events about this quote, order or agent")
    ] = None,
    from_: Annotated[datetime | None, Query(alias="from", description="Inclusive")] = None,
    to: Annotated[datetime | None, Query(description="Exclusive")] = None,
    cursor: Annotated[str | None, Query(description="`nextCursor` of the previous page")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AuditEventListResponse:
    try:
        page = await trail.list_events(
            session,
            organization_id=principal.organization.id,
            visible_to_agent_id=principal.agent.id if principal.agent else None,
            agent_public_id=agent_id,
            event_type=type,
            subject_public_id=subject,
            since=from_,
            until=to,
            cursor=cursor,
            limit=limit,
        )
    except InvalidCursorError as exc:
        raise InvalidCursor() from exc
    return AuditEventListResponse(
        items=[AuditEventOut.from_entry(entry) for entry in page.items],
        next_cursor=page.next_cursor,
    )
