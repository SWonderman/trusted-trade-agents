from typing import Annotated, Literal, get_args
from urllib.parse import quote

from mcp.server.mcpserver import Context, MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field, WithJsonSchema

from saint_elmo_mcp.auth import agent_key
from saint_elmo_mcp.backend import BackendClient, parse_response
from saint_elmo_mcp.schemas import (
    AllergenStrictness,
    CatalogVocabulary,
    Claim,
    ProductDetail,
    ProductSearchResult,
    Vocabulary,
)

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
- Each hit's `allergens` lists every excluded allergen, then every other
  allergen the product CONTAINS. `UNKNOWN` means there's no data, NOT safe. For
  strict kitchens use `declared_free`, which keeps only products explicitly
  declared free of every excluded allergen.
- If you get `UNKNOWN_CODE`, correct the listed codes (see `get_vocabulary`);
  don't drop the filter.
"""

GET_PRODUCT_DESCRIPTION = """\
Get the full catalog detail of one product by its Valio Aimo `code` (from
search_products).

Use it on a shortlisted product to check allergens or ingredients, or to see
curated substitutes, before quoting. Like search, it has NO live prices or stock.

- `allergens` lists every allergen with a declared status. An allergen that
  isn't listed is unknown, NOT absent: never treat it as "free from".
- Any other missing data (no ingredients, nutrients, origins) is likewise
  unknown, NOT absent.
- `curatedSubstitutes` are replacements Valio Aimo itself lists for the product.
- `PRODUCT_NOT_FOUND` means the code isn't in the catalog; search again.
"""

GET_VOCABULARY_DESCRIPTION = """\
Call this before using claim, diet, label, allergen or category filters on
search_products. Only codes that at least one product uses are listed.

- Each entry has its GS1 `name`, `definition` and `productCount`. A null name
  means the data uses a code GS1 doesn't list; it's still a valid filter code.
- Claims are `type` + `element` pairs: pass both codes to requiredClaims.
- Allergen `statusCounts` count only declared statuses. Products with no data
  are unknown, NOT free from the allergen.
- Category names aren't in the source data, only codes and counts.
- Pass `vocabularies` to get only the ones you need and save context.
"""

VocabularyName = Literal["claims", "diets", "labels", "allergens", "categories"]

CODES_HINT = "Valid codes: see get_vocabulary."

ALLERGEN_STRICTNESS_DESCRIPTION = (
    "How excludedAllergens filter. contains: drop products declared CONTAINS. "
    "may_contain: also drop MAY_CONTAIN. declared_free: keep only products declared "
    "FREE_FROM every excluded allergen. Products with no data are kept unless declared_free."
)


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
        excludedAllergens: Annotated[
            list[str] | None,
            Field(
                description="GS1 allergen codes to exclude, e.g. AM milk, AW gluten cereals; "
                f"allergenStrictness sets how. {CODES_HINT}"
            ),
        ] = None,
        # None means "not given": it's left out and the backend applies its default
        allergenStrictness: Annotated[
            AllergenStrictness | None,
            WithJsonSchema(
                {
                    "type": "string",
                    "enum": list(get_args(AllergenStrictness)),
                    "description": ALLERGEN_STRICTNESS_DESCRIPTION,
                }
            ),
            # Advertise the backend's default, not the Python sentinel
            Field(json_schema_extra=lambda schema: schema.update(default="contains")),
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
            "excludedAllergens": excludedAllergens,
            "allergenStrictness": allergenStrictness,
        }
        data = await backend.post(
            "/api/v1/products/search",
            agent_key=agent_key(ctx),
            json={k: v for k, v in body.items() if v is not None},
        )
        return parse_response(ProductSearchResult, data)

    @mcp.tool(
        description=GET_PRODUCT_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Get product",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_product(
        ctx: Context,
        code: Annotated[
            str, Field(description="Valio Aimo product code from search_products.")
        ],
        language: Annotated[
            Literal["en", "fi", "sv"],
            Field(
                description="Language of the product name; falls back to fi. Ingredient "
                "names come in every available language."
            ),
        ] = "en",
    ) -> ProductDetail:
        data = await backend.get(
            f"/api/v1/products/{quote(code, safe='')}",
            agent_key=agent_key(ctx),
            params={"language": language},
        )
        return parse_response(ProductDetail, data)

    @mcp.tool(
        description=GET_VOCABULARY_DESCRIPTION,
        annotations=ToolAnnotations(
            title="Get filter vocabulary",
            read_only_hint=True,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    )
    async def get_vocabulary(
        ctx: Context,
        vocabularies: Annotated[
            list[VocabularyName] | None,
            Field(min_length=1, description="Only these vocabularies. Omit for all five."),
        ] = None,
    ) -> Vocabulary:
        data = await backend.get("/api/v1/catalog/vocabulary", agent_key=agent_key(ctx))
        catalog_vocabulary = parse_response(CatalogVocabulary, data)
        # The backend has no subset parameter (#6); trimming the reply is presentation only
        wanted: set[str] = set(vocabularies or get_args(VocabularyName))
        return Vocabulary.model_validate(catalog_vocabulary.model_dump(include=wanted))
