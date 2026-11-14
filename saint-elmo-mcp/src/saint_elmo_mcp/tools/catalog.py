from typing import Annotated, Literal

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response
from saint_elmo_mcp.schemas import Claim, ProductSearchResult

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
- If you get `UNKNOWN_CODE`, correct the listed codes (see `get_vocabulary`);
  don't drop the filter.
"""

CODES_HINT = "Valid codes: see get_vocabulary."


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
        categoryCodes: Annotated[
            list[str] | None,
            Field(description=f"Product must be in ANY of these categories. {CODES_HINT}"),
        ] = None,
        vendors: Annotated[
            list[str] | None,
            Field(description="Product must come from ANY of these vendors, by name."),
        ] = None,
        requiredClaims: Annotated[
            list[Claim] | None,
            Field(
                description="Product must carry ALL of these claims, e.g. "
                f'{{"type": "FREE_FROM", "element": "LACTOSE"}}. {CODES_HINT}'
            ),
        ] = None,
        requiredDiets: Annotated[
            list[str] | None,
            Field(description=f"GS1 diet codes, e.g. VEGAN; product must carry ALL. {CODES_HINT}"),
        ] = None,
        requiredLabels: Annotated[
            list[str] | None,
            Field(
                description="Packaging label codes, e.g. EU_ORGANIC_FARMING; product must "
                f"carry ALL. {CODES_HINT}"
            ),
        ] = None,
        countriesOfOrigin: Annotated[
            list[str] | None,
            Field(description="ISO 3166-1 alpha-2 codes, e.g. fi; product must come from ANY."),
        ] = None,
        minDeliveryReliability: Annotated[
            float | None,
            Field(
                ge=0,
                le=1,
                description="Minimum share of ordered quantity delivered, 0-1. Also excludes "
                "products with no delivery history.",
            ),
        ] = None,
    ) -> ProductSearchResult:
        body = {
            "query": query,
            "language": language,
            "limit": limit,
            "offset": offset,
            "categoryCodes": categoryCodes,
            "vendors": vendors,
            "requiredClaims": (
                None
                if requiredClaims is None
                else [c.model_dump(by_alias=True) for c in requiredClaims]
            ),
            "requiredDiets": requiredDiets,
            "requiredLabels": requiredLabels,
            "countriesOfOrigin": countriesOfOrigin,
            "minDeliveryReliability": minDeliveryReliability,
        }
        data = await backend.post(
            "/api/v1/products/search",
            agent_key=agent_key(ctx),
            json={k: v for k, v in body.items() if v is not None},
        )
        return parse_response(ProductSearchResult, data)
