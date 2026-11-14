from typing import Annotated, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response
from saint_elmo_mcp.schemas import ProductSearchResult

SEARCH_PRODUCTS_DESCRIPTION = """\
Search the Valio Aimo product catalog (about 17,500 food-service products).

Searches the static catalog only. Results have NO live prices or stock: get
those for a shortlist with get_offers before you compare or order.

- `query` is free text matched against Finnish, Swedish and English product
  names at once, and tolerates typos. Leave it out to browse.
- Use the returned `code` (the Valio Aimo product code) with every other tool.
- `deliveryReliability` null means no delivery history, NOT unreliable.
- `carbonFootprint` is a product-group average, not a product-level figure.
- A claim, diet or label that isn't listed is unknown, NOT absent: never treat
  a missing allergen or claim as "free from".
"""


def register(mcp: MCPServer, backend: BackendClient) -> None:
    @mcp.tool(
        description=SEARCH_PRODUCTS_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Search products",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def search_products(
        ctx: Context,
        query: Annotated[
            str | None,
            Field(description='Free text, e.g. "lactose free milk". Omit to browse.'),
        ] = None,
        language: Annotated[
            Literal["en", "fi", "sv"],
            Field(description="Language of the returned texts; falls back to fi."),
        ] = "en",
        limit: Annotated[int, Field(ge=1, le=100, description="Page size.")] = 10,
        offset: Annotated[int, Field(ge=0, description="Items to skip.")] = 0,
    ) -> ProductSearchResult:
        body = {"query": query, "language": language, "limit": limit, "offset": offset}
        data = await backend.post(
            "/api/v1/products/search",
            agent_key=agent_key(ctx),
            json={k: v for k, v in body.items() if v is not None},
        )
        return parse_response(ProductSearchResult, data)
