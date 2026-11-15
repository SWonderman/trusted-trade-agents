from typing import Annotated
from urllib.parse import quote as url_quote
from uuid import UUID

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import AwareDatetime, Field

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response, request_body
from saint_elmo_mcp.schemas import AuditEventType, AuditLog

# The backend's list allows 1-200 (api/v1/routes/audit.py); change them together.
# The default is ours, smaller than the backend's 50, to save the agent's context.
MAX_LIMIT = 200
DEFAULT_LIMIT = 20

GET_AUDIT_LOG_DESCRIPTION = """\
Read the audit trail: what you decided and committed to, and why it went the way
it did. Use it to explain your actions to the buyer.

- The trail records decisions and commitments (quotes, substitute requests,
  orders, approvals), not lookups such as searches or price checks.
- You see your own events, plus human approvals and rejections of your orders
  and the automatic steps on them.
- To explain one order to the buyer, pass `order_id`: you get that order's whole
  trail, oldest first, from its first quote (and the quotes it revised) to its
  latest event. `event_type` and `since` still filter it; `limit` doesn't apply.
- Without `order_id` you get your events, newest first, `limit` at a time. Pass
  `nextCursor` back as `cursor` for older ones.
- Quote each event's `summary` to the buyer rather than re-deriving it from
  payloads. Set `include_payload` only when you need the recorded data itself.
- `ORDER_NOT_FOUND`: no order of yours with this id. `PERMISSION_DENIED`: your
  agent token lacks the `audit:read` scope. You can't fix this; tell the buyer
  to ask a buyer admin for it.
"""


def register(mcp: MCPServer, backend: BackendClient) -> None:
    @mcp.tool(
        description=GET_AUDIT_LOG_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Get audit log",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_audit_log(
        ctx: Context,
        order_id: Annotated[
            UUID | None,
            Field(description="An orderId: read that order's whole trail instead of your events."),
        ] = None,
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
            Field(
                min_length=1,
                description="`nextCursor` from the previous call, for older events. Not with "
                "order_id.",
            ),
        ] = None,
        limit: Annotated[
            int,
            Field(
                ge=1,
                le=MAX_LIMIT,
                description=f"Most events to return, 1-{MAX_LIMIT}. Not for an order trail.",
            ),
        ] = DEFAULT_LIMIT,
        include_payload: Annotated[
            bool,
            Field(description="Include each event's recorded data. Large; off by default."),
        ] = False,
    ) -> AuditLog:
        if order_id is not None:
            if cursor is not None:
                raise ToolError(
                    "VALIDATION_ERROR: `cursor` pages your event list; an order trail comes "
                    "whole. Drop `cursor` or `order_id`."
                )
            data = await backend.get(
                f"/api/v1/orders/{url_quote(str(order_id), safe='')}/trail",
                agent_key=agent_key(ctx),
            )
            log = parse_response(AuditLog, data)
            log.items = [
                event
                for event in log.items
                if (event_type is None or event.type == event_type)
                and (since is None or event.at >= since)
            ]
        else:
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
        if not include_payload:
            for event in log.items:
                event.payload = None
        return log
