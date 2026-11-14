from datetime import date
from typing import Annotated
from urllib.parse import quote as url_quote
from uuid import UUID

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response, request_body
from saint_elmo_mcp.schemas import Quote, QuoteLineIn

# Mirror the backend's bounds (quotes/schemas.py MAX_LINES, MAX_TEXT_LENGTH);
# change them together
MAX_LINES = 50
MAX_TEXT_LENGTH = 2000

CREATE_QUOTE_DESCRIPTION = """\
Turn the basket you chose (after get_offers) into a quote: each line converted
to sales units, priced from live offers on `deliverBy`, and judged against your
mandate. A quote binds nothing; place_order commits it. Each call creates a new
quote.

- Give quantities in the buyer's units (L or KG, e.g. 1000 L), as with
  get_offers. Don't do unit arithmetic yourself.
- Set `substitutesFor` on a line that replaces another product, so the mandate's
  substitution rules and price-increase limit apply to it.
- `buyerRequest` is the buyer's need in their own words; `rationale` is why you
  chose these lines. Both are shown to approvers and kept in the audit trail.
  Neither changes the policy result.
- `policy.outcome` REJECT or NEEDS_HUMAN is an answer, not an error. Read
  `policy.reasons` (and each line's `reasons`), then revise and quote again with
  `previousQuoteId`, or explain the outcome to the buyer.
- The quote expires at `expiresAt`; place_order it before then.
- `PRODUCT_NOT_FOUND` lists every unknown code; fix them (search_products).
- `QUOTE_NOT_FOUND`: `previousQuoteId` isn't a quote of your organisation.
- `CUSTOMER_NUMBER_MISSING`: your buyer organisation isn't set up with a Valio
  Aimo customer number. You can't fix this; tell the buyer to contact a buyer admin.
- `VALIO_AIMO_UNAVAILABLE`: the Valio Aimo API is down. Try again later.
"""

GET_QUOTE_DESCRIPTION = """\
Read a quote of your buyer organisation exactly as it was quoted: lines, totals,
deposits and policy outcome. `status: "EXPIRED"` means it is past `expiresAt`
and can't be ordered any more: create a new quote (with `previousQuoteId`).
`QUOTE_NOT_FOUND`: no quote with this id in your organisation.
"""


def register(mcp: MCPServer, backend: BackendClient) -> None:
    @mcp.tool(
        description=CREATE_QUOTE_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Create quote",
            read_only_hint=False,
            destructive_hint=False,
            idempotent_hint=False,
            open_world_hint=False,
        ),
    )
    async def create_quote(
        ctx: Context,
        deliverBy: Annotated[
            date,
            Field(
                description="Delivery date as an ISO date (YYYY-MM-DD). Resolve relative "
                'dates like "by Monday" yourself.',
            ),
        ],
        lines: Annotated[
            list[QuoteLineIn],
            Field(
                min_length=1,
                max_length=MAX_LINES,
                description=f"The basket, 1-{MAX_LINES} lines.",
            ),
        ],
        buyerRequest: Annotated[
            str,
            Field(
                min_length=1,
                max_length=MAX_TEXT_LENGTH,
                description="The buyer's need in their own words, e.g. \"1,000 litres of "
                'lactose-free milk by Monday". Shown to approvers; never affects the policy.',
            ),
        ],
        rationale: Annotated[
            str,
            Field(
                min_length=1,
                max_length=MAX_TEXT_LENGTH,
                description="Why you chose these lines. Shown to approvers; never affects "
                "the policy.",
            ),
        ],
        previousQuoteId: Annotated[
            UUID | None,
            Field(description="The quote this one revises, so the attempts stay connected."),
        ] = None,
    ) -> Quote:
        data = await backend.post(
            "/api/v1/quotes",
            agent_key=agent_key(ctx),
            json=request_body(
                deliverBy=deliverBy.isoformat(),
                lines=[line.model_dump(by_alias=True, exclude_none=True) for line in lines],
                buyerRequest=buyerRequest,
                rationale=rationale,
                previousQuoteId=str(previousQuoteId) if previousQuoteId else None,
            ),
        )
        return parse_response(Quote, data)

    @mcp.tool(
        description=GET_QUOTE_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Get quote",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_quote(
        ctx: Context,
        quoteId: Annotated[UUID, Field(description="The quoteId from create_quote.")],
    ) -> Quote:
        data = await backend.get(
            f"/api/v1/quotes/{url_quote(str(quoteId), safe='')}", agent_key=agent_key(ctx)
        )
        return parse_response(Quote, data)
