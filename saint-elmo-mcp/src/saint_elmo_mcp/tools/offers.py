from datetime import date
from typing import Annotated, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response, request_body
from saint_elmo_mcp.schemas import OfferItem, Offers

# Mirrors the backend's bound (offers/schemas.py MAX_ITEMS); change them together
MAX_ITEMS = 50

GET_OFFERS_DESCRIPTION = """\
Get live Valio Aimo price and availability for a shortlist of products (from
search_products / get_product) for one delivery date, priced for your buyer
organisation. Offers are live and binding on nothing: use create_quote to commit.

- Give `quantity` with `unit` L or KG (e.g. 1000 L) to have it converted to
  sales units and priced. Don't do unit arithmetic yourself. Without a unit,
  `quantity` is in the product's sales unit.
- Before choosing, check each item's `availability.meetsDeadline`,
  `reasonCodes` and `quantity.conversion.crossCheck` (DISAGREES or
  CONVERSION_UNCERTAIN: double-check the amount before ordering).
- `availableAmount: null` means unknown (supplier-shipped TERMINAL products),
  NOT zero. `coveredByAvailability: null` is likewise unknown.
- `CLOSING_TIME_PASSED` means today's order cut-off for that delivery date has
  passed, so the line misses the deadline even if stock exists. Pick a later
  `deliverBy` or another product.
- `provenance.validUntil` is when the offer goes stale; fetch again after it.
- `PRODUCT_NOT_FOUND` lists every unknown code; fix them (search_products).
- `CUSTOMER_NUMBER_MISSING`: your buyer organisation isn't set up with a Valio
  Aimo customer number. You can't fix this; tell the buyer to contact a buyer admin.
- `VALIO_AIMO_UNAVAILABLE`: the Valio Aimo API is down. Try again later.
"""


def register(mcp: MCPServer, backend: BackendClient) -> None:
    @mcp.tool(
        description=GET_OFFERS_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Get live offers",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_offers(
        ctx: Context,
        deliverBy: Annotated[
            date,
            Field(
                description='Delivery date as an ISO date (YYYY-MM-DD). Resolve relative '
                'dates like "by Monday" yourself.',
            ),
        ],
        items: Annotated[
            list[OfferItem],
            Field(
                min_length=1,
                max_length=MAX_ITEMS,
                description=f"Products to offer, 1-{MAX_ITEMS}, each with an optional quantity.",
            ),
        ],
        # None means "not given": it's left out and the backend applies its default (en)
        language: Annotated[
            Literal["en", "fi", "sv"] | None,
            Field(description="Language of product names; defaults to en, falls back to fi."),
        ] = None,
    ) -> Offers:
        data = await backend.post(
            "/api/v1/offers",
            agent_key=agent_key(ctx),
            json=request_body(
                deliverBy=deliverBy.isoformat(),
                items=[item.model_dump(by_alias=True, exclude_none=True) for item in items],
                language=language,
            ),
        )
        return parse_response(Offers, data)
