from typing import Annotated
from urllib.parse import quote as url_quote
from uuid import UUID

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response, request_body
from saint_elmo_mcp.schemas import Order, OrderList, OrderStatus

# Mirror the backend's list_orders query bounds; change them together
MAX_LIMIT = 100

# There is deliberately no approve or reject tool: approval is user-only (#15), and
# an agent can never approve its own orders.

PLACE_ORDER_DESCRIPTION = """\
Commit a quote (from create_quote) as an order. Retrying is safe: the quote id is
the idempotency key, so one quote never gives two orders.

- The backend re-checks live price, availability and your current mandate when
  you place the order, so the outcome can differ from the quote. Read `changes`
  (what moved since the quote) and `policy.reasons`.
- `status: "PLACED"`: done.
- `status: "PENDING_APPROVAL"`: a human decides. Tell the buyer the order is
  waiting for approval, and poll get_order_status no sooner than
  `checkAgainAfterSeconds`. You can't approve it yourself.
- `status: "REJECTED"` is an answer with reasons, not an error. Read
  `policy.reasons`, then revise with a new quote or explain it to the buyer.
- `QUOTE_EXPIRED`: create a new quote (with `previousQuoteId`) and order that.
- `QUOTE_ALREADY_ORDERED`: this quote already has an order. Use the `orderId` in
  the error with get_order_status instead of ordering again.
- `QUOTE_NOT_FOUND`: no quote of yours with this id.
- `VALIO_AIMO_UNAVAILABLE`: the Valio Aimo API is down. Try again later.
"""

GET_ORDER_STATUS_DESCRIPTION = """\
Read one of your orders: status, lines, totals, policy outcome and what changed
since the quote. While `status` is "PENDING_APPROVAL", poll no sooner than
`checkAgainAfterSeconds`. Once a human decided, `statusHistory` says who and when
and `approverNote` says why; pass that on to the buyer.
`ORDER_NOT_FOUND`: no order of yours with this id.
"""

LIST_ORDERS_DESCRIPTION = """\
List your orders, most recent first, optionally only those in one status (e.g.
PENDING_APPROVAL to see what is waiting for a human). `total` counts every match;
page with `limit` and `offset`. Use get_order_status to follow one order.
"""


def register(mcp: MCPServer, backend: BackendClient) -> None:
    @mcp.tool(
        description=PLACE_ORDER_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Place order",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def place_order(
        ctx: Context,
        quoteId: Annotated[UUID, Field(description="The quoteId from create_quote.")],
    ) -> Order:
        data = await backend.post(
            "/api/v1/orders", agent_key=agent_key(ctx), json={"quoteId": str(quoteId)}
        )
        return parse_response(Order, data)

    @mcp.tool(
        description=GET_ORDER_STATUS_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Get order status",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_order_status(
        ctx: Context,
        orderId: Annotated[UUID, Field(description="The orderId from place_order.")],
    ) -> Order:
        data = await backend.get(
            f"/api/v1/orders/{url_quote(str(orderId), safe='')}", agent_key=agent_key(ctx)
        )
        return parse_response(Order, data)

    @mcp.tool(
        description=LIST_ORDERS_DESCRIPTION,
        annotations=ToolAnnotations(
            title="List orders",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def list_orders(
        ctx: Context,
        status: Annotated[
            OrderStatus | None, Field(description="Only orders in this status.")
        ] = None,
        limit: Annotated[
            int | None,
            Field(ge=1, le=MAX_LIMIT, description=f"Page size, 1-{MAX_LIMIT}; default 20."),
        ] = None,
        offset: Annotated[
            int | None, Field(ge=0, description="Orders to skip; default 0.")
        ] = None,
    ) -> OrderList:
        data = await backend.get(
            "/api/v1/orders",
            agent_key=agent_key(ctx),
            params=request_body(status=status, limit=limit, offset=offset),
        )
        return parse_response(OrderList, data)
