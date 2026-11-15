from typing import Annotated
from urllib.parse import quote as url_quote
from uuid import UUID

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import AwareDatetime, Field

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response, request_body
from saint_elmo_mcp.schemas import AuditEvent, AuditEventType, AuditLog, OrderTrail

# The backend's list allows 1-200 (api/v1/routes/audit.py); change them together.
# The default is ours, smaller than the backend's 50, to save the agent's context.
MAX_LIMIT = 200
DEFAULT_LIMIT = 20

AUDIT_TRAIL_BASICS = """\
- The trail records decisions and commitments (quotes, substitute requests,
  orders, approvals), not lookups such as searches or price checks.
- You see your own events, plus human approvals and rejections of your orders
  and the automatic steps on them.
- Quote each event's `summary` to the buyer rather than re-deriving it from
  payloads. Set `include_payload` only when you need the recorded data itself.
- `PERMISSION_DENIED`: your agent token lacks the `audit:read` scope. You can't
  fix this; tell the buyer to ask a buyer admin for it.
"""

GET_ORDER_TRAIL_DESCRIPTION = f"""\
Read one order's whole audit trail, oldest first: from its first quote (and the
quotes it revised) to its latest event. Use it to explain to the buyer what you
did and why the order went the way it did.

{AUDIT_TRAIL_BASICS}- `ORDER_NOT_FOUND`: no order of yours with this id.
"""

GET_AUDIT_LOG_DESCRIPTION = f"""\
List your audit events, newest first, `limit` at a time; pass `nextCursor` back
as `cursor` for older ones. Use it to recall what you did recently. To explain
one order, use get_order_trail instead.

{AUDIT_TRAIL_BASICS}- `VALIDATION_ERROR` on `cursor`: pass a `nextCursor` exactly as returned.
"""

INCLUDE_PAYLOAD_DESCRIPTION = (
    "Include each event's recorded data. Large; off by default."
)

READ_ONLY = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=False
)


def _drop_payloads(events: list[AuditEvent], include_payload: bool) -> None:
    if not include_payload:
        for event in events:
            event.payload = None


def register(mcp: MCPServer, backend: BackendClient) -> None:
    @mcp.tool(
        description=GET_ORDER_TRAIL_DESCRIPTION,
        annotations=READ_ONLY.model_copy(update={"title": "Get order trail"}),
    )
    async def get_order_trail(
        ctx: Context,
        order_id: Annotated[UUID, Field(description="The orderId from place_order.")],
        include_payload: Annotated[
            bool, Field(description=INCLUDE_PAYLOAD_DESCRIPTION)
        ] = False,
    ) -> OrderTrail:
        data = await backend.get(
            f"/api/v1/orders/{url_quote(str(order_id), safe='')}/trail",
            agent_key=agent_key(ctx),
        )
        trail = parse_response(OrderTrail, data)
        _drop_payloads(trail.items, include_payload)
        return trail

    @mcp.tool(
        description=GET_AUDIT_LOG_DESCRIPTION,
        annotations=READ_ONLY.model_copy(update={"title": "Get audit log"}),
    )
    async def get_audit_log(
        ctx: Context,
        event_type: Annotated[
            AuditEventType | None, Field(description="Only events of this type.")
        ] = None,
        since: Annotated[
            AwareDatetime | None,
            Field(
                description="Only events at or after this ISO date-time, with an offset, "
                "e.g. 2026-11-14T00:00:00+02:00."
            ),
        ] = None,
        cursor: Annotated[
            str | None,
            Field(min_length=1, description="`nextCursor` from the previous call."),
        ] = None,
        limit: Annotated[
            int,
            Field(
                ge=1, le=MAX_LIMIT, description=f"Most events to return, 1-{MAX_LIMIT}."
            ),
        ] = DEFAULT_LIMIT,
        include_payload: Annotated[
            bool, Field(description=INCLUDE_PAYLOAD_DESCRIPTION)
        ] = False,
    ) -> AuditLog:
        data = await backend.get(
            "/api/v1/audit-events",
            agent_key=agent_key(ctx),
            params=request_body(
                type=event_type,
                **{"from": None if since is None else since.isoformat()},
                cursor=cursor,
                limit=limit,
            ),
        )
        log = parse_response(AuditLog, data)
        _drop_payloads(log.items, include_payload)
        return log
