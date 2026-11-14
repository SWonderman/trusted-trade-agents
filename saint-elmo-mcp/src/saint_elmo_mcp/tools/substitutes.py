from datetime import date
from typing import Annotated, Literal
from urllib.parse import quote

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field, StringConstraints, WithJsonSchema

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response, request_body
from saint_elmo_mcp.schemas import Claim, Substitutes

# Mirror the backend's bounds (substitutes/schemas.py); change them together
MAX_LIMIT = 10
DEFAULT_LIMIT = 3

CODES_HINT = "Valid codes: see get_vocabulary."

FIND_SUBSTITUTES_DESCRIPTION = """\
Get ranked substitutes, labelled BEST / BETTER / GOOD, for a product that
can't meet the need. Call this when an offer or quote line has a shortfall
(PARTIAL_AVAILABILITY, LATE_DELIVERY, NOT_DELIVERABLE, SALES_BLOCKED).

- Your mandate's requirements always apply. The filters here can only tighten
  them, never loosen them.
- Give the same `quantity` + `unit` and `deliverBy` as the original line, so
  candidates are judged on covering that need. Each candidate's `offer` is a
  live offer, as get_offers returns it.
- `tradeOffs` compares each candidate with the original: price per buyer unit,
  earliest date, delivery reliability and CO2 deltas (null = unknown), and the
  claims and labels kept, lost and gained. The CO2 delta is a
  product-group estimate, not a product-level measurement.
- `policyPreview` shows whether choosing a candidate would need approval (e.g.
  SUBSTITUTE_NEEDS_APPROVAL). It's a preview, not a commitment.
- To choose one, re-quote with create_quote, setting the candidate line's
  `substitutesFor` to the original code, and explain the trade-off in
  `rationale`.
- An empty `candidates` list with `NO_SUBSTITUTES_FOUND` is an answer: tell
  the buyer.
- `PRODUCT_NOT_FOUND`: the code isn't in the catalog. `UNKNOWN_CODE`: correct
  the listed filter codes (see get_vocabulary); don't drop the filter.
  `VALIO_AIMO_UNAVAILABLE`: the Valio Aimo API is down. Try again later.
"""


def register(mcp: MCPServer, backend: BackendClient) -> None:
    @mcp.tool(
        description=FIND_SUBSTITUTES_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Find substitutes",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def find_substitutes(
        ctx: Context,
        code: Annotated[
            str,
            Field(min_length=1, description="Valio Aimo product code of the original product."),
        ],
        quantity: Annotated[
            float | None,
            Field(
                gt=0,
                description="How much the buyer needs, in `unit`. With it, candidates are "
                "judged on covering it and their offers are priced for it.",
            ),
        ] = None,
        unit: Annotated[
            str | None,
            Field(
                min_length=1,
                max_length=10,
                description="Unit of `quantity`: L, KG, or a unit code such as KI. Omit for "
                "the original's sales unit. Needs `quantity`.",
            ),
        ] = None,
        deliverBy: Annotated[
            date | None,
            Field(
                description="Delivery date as an ISO date (YYYY-MM-DD). Omit for tomorrow "
                "(Europe/Helsinki)."
            ),
        ] = None,
        requiredClaims: Annotated[
            list[Claim] | None,
            Field(description=f"Added to the mandate's; a candidate must carry ALL. {CODES_HINT}"),
        ] = None,
        requiredLabels: Annotated[
            list[str] | None,
            Field(description=f"Label codes added to the mandate's. {CODES_HINT}"),
        ] = None,
        requiredDiets: Annotated[
            list[str] | None,
            Field(description=f"GS1 diet codes added to the mandate's. {CODES_HINT}"),
        ] = None,
        excludedAllergens: Annotated[
            list[str] | None,
            Field(
                description="GS1 allergen codes added to the mandate's, excluded as strictly "
                f"as the mandate's allergenStrictness says. {CODES_HINT}"
            ),
        ] = None,
        countriesOfOrigin: Annotated[
            list[Annotated[str, StringConstraints(pattern=r"^[A-Za-z]{2}$")]] | None,
            Field(
                description="ISO 3166-1 alpha-2 codes, e.g. fi; a candidate must come from ANY "
                "of them, and from the mandate's allowed origins if it has any."
            ),
        ] = None,
        minDeliveryReliability: Annotated[
            float | None,
            Field(
                ge=0,
                le=1,
                description="Minimum share of ordered quantity delivered, 0-1. Also excludes "
                "candidates with no delivery history. The mandate's own minimum still applies.",
            ),
        ] = None,
        # None means "not given": it's left out and the backend applies its default
        limit: Annotated[
            int | None,
            WithJsonSchema(
                {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": MAX_LIMIT,
                    "default": DEFAULT_LIMIT,
                    "description": f"Most candidates to return, 1-{MAX_LIMIT}.",
                }
            ),
            Field(ge=1, le=MAX_LIMIT),
        ] = None,
        language: Annotated[
            Literal["en", "fi", "sv"] | None,
            Field(description="Language of product names; defaults to en, falls back to fi."),
        ] = None,
    ) -> Substitutes:
        # Mirrors the backend's SubstitutesIn._unit_needs_quantity
        if unit is not None and quantity is None:
            raise ToolError("VALIDATION_ERROR: `unit` needs `quantity`; give both or neither.")
        data = await backend.post(
            f"/api/v1/products/{quote(code, safe='')}/substitutes",
            agent_key=agent_key(ctx),
            json=request_body(
                quantity=quantity,
                unit=unit,
                deliverBy=None if deliverBy is None else deliverBy.isoformat(),
                requiredClaims=(
                    None
                    if requiredClaims is None
                    else [c.model_dump(by_alias=True) for c in requiredClaims]
                ),
                requiredLabels=requiredLabels,
                requiredDiets=requiredDiets,
                excludedAllergens=excludedAllergens,
                countriesOfOrigin=countriesOfOrigin,
                minDeliveryReliability=minDeliveryReliability,
                limit=limit,
                language=language,
            ),
        )
        return parse_response(Substitutes, data)
