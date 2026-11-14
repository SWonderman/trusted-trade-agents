"""Tool output models.

These copy only the parts of the backend's response shapes that an agent needs,
under the same camelCase names. Extra backend fields are ignored. A missing or
renamed field fails validation, which is how contract drift shows up in tests
(ADR 0001).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="ignore"
    )


# --- Catalog search (POST /api/v1/products/search, issue #2) ---


class Provenance(CamelModel):
    source: str = Field(description="Where the data comes from.")
    catalog_snapshot_date: str | None = Field(
        default=None, description="Date of the static catalog snapshot (ISO date)."
    )


class ProductUnit(CamelModel):
    code: str = Field(description="Unit code, e.g. KI, ST, PAK.")
    size_in_base_units: float | None = None


class Claim(CamelModel):
    type: str = Field(description="GS1 claim type, e.g. FREE_FROM.")
    element: str = Field(description="GS1 claim element, e.g. LACTOSE.")


class CarbonFootprint(CamelModel):
    value: float = Field(description="kg CO2-eq per kg.")
    basis: Literal["PRODUCT_GROUP_AVERAGE"] = Field(
        description="Always a product-group average, never a product-level measurement."
    )


class HitAllergen(CamelModel):
    code: str = Field(description="GS1 allergen type code, e.g. AM milk.")
    status: Literal["CONTAINS", "MAY_CONTAIN", "FREE_FROM", "UNDECLARED", "UNKNOWN"] = Field(
        description="UNKNOWN = no data for this allergen, NOT safe. Only FREE_FROM is a "
        "declaration that the product is free of it."
    )


class ProductHit(CamelModel):
    code: str = Field(description="Valio Aimo product code; use it with every other tool.")
    name: str | None = None
    gtin: str | None = None
    category_code: str | None = None
    vendor: str | None = None
    brand: str | None = None
    sales_unit: str = Field(description="Unit the product is ordered and priced in.")
    base_unit: str | None = None
    allowed_lot_size: float | None = Field(
        default=None, description="Ordered sales units must be a multiple of this."
    )
    units: list[ProductUnit] = []
    variable_unit: bool | None = None
    has_deposit: bool | None = None
    claims: list[Claim] = []
    diets: list[str] = []
    labels: list[str] = []
    country_of_origin: str | None = None
    delivery_reliability: float | None = Field(
        default=None,
        description="Share of ordered quantity delivered, 0-1. null = no history, NOT unreliable.",
    )
    carbon_footprint: CarbonFootprint | None = None
    relevance: float | None = None
    allergens: list[HitAllergen] = Field(
        description="Every excluded allergen, in request order, then every other allergen "
        "the product CONTAINS. Not a full allergen list."
    )


class ProductSearchResult(CamelModel):
    total: int = Field(description="Number of matching products across all pages.")
    items: list[ProductHit]
    provenance: Provenance
