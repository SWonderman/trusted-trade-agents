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


class ProductSummary(CamelModel):
    """Fields shared by a search hit and the product detail."""

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


class ProductHit(ProductSummary):
    relevance: float | None = None
    allergens: list[HitAllergen] = Field(
        description="Every excluded allergen, in request order, then every other allergen "
        "the product CONTAINS. Not a full allergen list."
    )


class ProductSearchResult(CamelModel):
    total: int = Field(description="Number of matching products across all pages.")
    items: list[ProductHit]
    provenance: Provenance


# --- Product detail (GET /api/v1/products/{code}, issue #5) ---


class Allergen(CamelModel):
    code: str = Field(description="GS1 allergen type code, e.g. AM milk.")
    name: str | None = None
    containment: Literal["CONTAINS", "MAY_CONTAIN", "UNDECLARED", "FREE_FROM"] = Field(
        description="An allergen missing from the list is UNKNOWN, NOT free from it."
    )


class Nutrient(CamelModel):
    code: str = Field(description="GS1 nutrient type, e.g. FAT, ENER-, LACS (lactose).")
    value: float
    unit: str = Field(description="GS1 measurement unit, e.g. GRM, KJO.")
    precision: str | None = Field(default=None, description="e.g. APPROXIMATELY, LESS_THAN.")
    basis_quantity: float | None = Field(
        default=None, description="The value is per this quantity, usually 100."
    )
    basis_unit: str | None = None
    daily_value_percent: float | None = None
    serving_size: float | None = None
    serving_size_unit: str | None = None


class IngredientOrigin(CamelModel):
    stage: str = Field(description="GS1 production stage, e.g. FARMING, MILKING.")
    country: str = Field(description="ISO 3166-1 numeric, or NON_EU.")


class Ingredient(CamelModel):
    sequence: int = Field(description="Position in the ingredient list, from 1.")
    percentage: float | None = None
    names: dict[str, str] = Field(
        description="Name per ISO 639-1 language, every language available (not only the "
        "requested one)."
    )
    origins: list[IngredientOrigin] = []


class PackagingLevelDimensions(CamelModel):
    level: Literal["BASE_UNIT_OR_EACH", "CASE", "PALLET"]
    length_mm: float | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    gross_weight_g: float | None = None
    net_weight_g: float | None = None
    volume_value: float | None = None
    volume_unit: str | None = Field(
        default=None, description="As declared: may be a volume, weight or count unit."
    )


class Deposit(CamelModel):
    material_code: str = Field(description="Deposit material code; not a catalog product.")
    quantity: float = Field(description="Deposit units per sales unit.")
    unit: str


class Producer(CamelModel):
    name: str
    gln: str = Field(description="GS1 Global Location Number of the manufacturer.")


class CuratedSubstitute(CamelModel):
    code: str = Field(description="Valio Aimo product code of the substitute.")
    name: str | None = None


class ProductDetail(ProductSummary):
    allergens: list[Allergen] = Field(
        description="Every allergen with a declared status. One not listed is UNKNOWN, NOT safe."
    )
    ingredients: list[Ingredient] = Field(description="In ingredient list order.")
    nutrients: list[Nutrient]
    packaging_levels: list[PackagingLevelDimensions] = Field(
        description="Manufacturer-declared dimensions and weights, in mm and grams."
    )
    deposits: list[Deposit]
    producers: list[Producer]
    curated_substitutes: list[CuratedSubstitute] = Field(
        description="Replacements Valio Aimo itself lists for this product."
    )
    provenance: Provenance


# --- Catalog vocabulary (GET /api/v1/catalog/vocabulary, issue #6) ---


def _is_none(value: object) -> bool:
    return value is None


class VocabularyGS1Code(CamelModel):
    code: str
    # Required though nullable, as in the backend: a dropped field is contract drift
    name: str | None = Field(
        description="GS1 name; null for codes the data uses but GS1 doesn't list."
    )
    definition: str | None


class VocabularyCode(VocabularyGS1Code):
    product_count: int = Field(description="Number of products using the code.")


class AllergenStatusCounts(CamelModel):
    contains: int
    may_contain: int
    undeclared: int
    free_from: int


class VocabularyAllergen(VocabularyGS1Code):
    product_count: int = Field(
        description="Products declaring any status for the allergen (sum of statusCounts)."
    )
    status_counts: AllergenStatusCounts = Field(
        description="Products per declared status. Products with no declaration are unknown "
        "and not counted: no data is never FREE_FROM."
    )


class VocabularyClaim(CamelModel):
    type: VocabularyGS1Code = Field(description="GS1 claim type, e.g. FREE_FROM.")
    element: VocabularyGS1Code = Field(description="GS1 claim element, e.g. LACTOSE.")
    product_count: int = Field(description="Number of products making this claim.")


class VocabularyCategory(CamelModel):
    code: str = Field(description="Category code; names are not in the source data.")
    product_count: int


class CatalogVocabulary(CamelModel):
    """The backend's full reply. Every vocabulary is required, so drift fails loudly."""

    claims: list[VocabularyClaim]
    diets: list[VocabularyCode]
    labels: list[VocabularyCode]
    allergens: list[VocabularyAllergen]
    categories: list[VocabularyCategory]


class Vocabulary(CamelModel):
    """Tool output: valid filter codes. A vocabulary that wasn't asked for is left out."""

    claims: list[VocabularyClaim] | None = Field(
        default=None,
        exclude_if=_is_none,
        description="Claim type + element pairs, for requiredClaims.",
    )
    diets: list[VocabularyCode] | None = Field(
        default=None, exclude_if=_is_none, description="GS1 diet codes, for requiredDiets."
    )
    labels: list[VocabularyCode] | None = Field(
        default=None, exclude_if=_is_none, description="Label codes, for requiredLabels."
    )
    allergens: list[VocabularyAllergen] | None = Field(
        default=None,
        exclude_if=_is_none,
        description="GS1 allergen codes, for excludedAllergens.",
    )
    categories: list[VocabularyCategory] | None = Field(
        default=None, exclude_if=_is_none, description="Category codes, for categoryCodes."
    )


# --- Live offers (POST /api/v1/offers, issue #12) ---


class OfferItem(CamelModel):
    """One requested product. Tool input, sent to the backend as given."""

    # Bounds mirror the backend's OfferProductRequest
    product_code: str = Field(
        min_length=1, max_length=20, description="Valio Aimo product code from search_products."
    )
    quantity: float | None = Field(
        default=None,
        gt=0,
        description="Optional. With it, the line is converted to sales units and priced.",
    )
    unit: str | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        description="Unit of `quantity`: L, KG, or one of the product's unit codes (e.g. KI, "
        "ST). Give L or KG to get the conversion to sales units. Omit for sales units. "
        "Needs `quantity`.",
    )


class Money(CamelModel):
    net: float
    gross: float


class Measure(CamelModel):
    value: float
    unit: str


class OfferPrice(CamelModel):
    per_sales_unit: Money
    tax_rate: float | None = Field(description="Percent, e.g. 14.0.")
    currency: str
    comparison_price: Measure | None = Field(description="Price per litre or kilogram.")
    customer_specific: bool = Field(
        description="A price negotiated for your buyer organisation."
    )
    valid_from: str | None
    valid_to: str | None


class OfferAvailability(CamelModel):
    logistic_model: Literal["STOCK", "TERMINAL"] | None = Field(
        description="STOCK from Valio Aimo's warehouse, TERMINAL shipped by a supplier."
    )
    available_amount: float | None = Field(
        description="In sales units. null = unknown (always for TERMINAL), NOT zero."
    )
    available_amount_known: bool
    earliest_date: str | None = Field(description="Soonest delivery date; null if none.")
    closing_time: str | None = Field(description="Order cut-off for the date.")
    sales_blocked: bool
    meets_deadline: bool = Field(
        description="Deliverable by deliverBy and the closing time has not passed."
    )


class OfferConversion(CamelModel):
    per_sales_unit: Measure = Field(description="Requested units in one sales unit.")
    basis: Literal["PRICE_COMPARISON", "PACKAGING_UNITS"]
    cross_check: Literal["AGREES", "DISAGREES", "UNCHECKED"] = Field(
        description="Whether the product name or packaging agrees with the conversion. "
        "DISAGREES: verify before ordering."
    )


class OfferQuantity(CamelModel):
    requested: Measure
    conversion: OfferConversion | None = Field(
        description="null when the quantity was in sales units or couldn't be converted."
    )
    sales_units: float | None = Field(
        description="Rounded up to whole sales units, then to the lot size; null if the "
        "quantity couldn't be converted."
    )
    lot_size: float
    rounded_up: bool | None
    delivered: Measure | None = Field(description="What the buyer gets, in the requested unit.")
    line_total: Money | None = Field(description="null without a price or sales units.")
    covered_by_availability: bool | None = Field(
        description="null when the available amount is unknown, NOT uncovered."
    )


class OfferProvenance(CamelModel):
    source: str
    fetched_at: str
    valid_until: str | None = Field(
        description="The earliest of the price's validTo and the closing time."
    )
    cached: bool


OfferReasonCode = Literal[
    "PARTIAL_AVAILABILITY",
    "LATE_DELIVERY",
    "NOT_DELIVERABLE",
    "SALES_BLOCKED",
    "NO_PRICE",
    "CLOSING_TIME_PASSED",
    "CONVERSION_UNAVAILABLE",
    "CONVERSION_UNCERTAIN",
]


class Offer(CamelModel):
    product_code: str
    name: str | None
    sales_unit: str
    price: OfferPrice | None = Field(description="null when there is no price (NO_PRICE).")
    availability: OfferAvailability | None = Field(
        description="null when the product can't be delivered (NOT_DELIVERABLE)."
    )
    quantity: OfferQuantity | None = Field(description="null when no quantity was given.")
    delivery_reliability: float | None = Field(
        description="Share of ordered quantity delivered, 0-1. null = no history."
    )
    carbon_footprint: CarbonFootprint | None
    reason_codes: list[OfferReasonCode] = Field(
        description="Shortfalls and data gaps; empty = none. An offer only states them, "
        "it judges nothing."
    )
    provenance: OfferProvenance


class Offers(CamelModel):
    deliver_by: str = Field(description="The delivery date the offers are for; check it.")
    evaluated_at: str
    items: list[Offer] = Field(description="One per requested item, in request order.")


# --- Agent mandate (GET /api/v1/agents/me/mandate, issue #11) ---
# Every field of the backend's MandateResponse, nothing hidden (ADR 0002). The
# enums are Literals copied from the backend, so a new value fails loudly.


class MandateAgent(CamelModel):
    id: str
    name: str


class MandateBuyerOrganisation(CamelModel):
    name: str


class CategorySpendCap(CamelModel):
    category_code: str
    cap: float = Field(description="EUR excluding VAT, per spend period.")


class PeriodSpend(CamelModel):
    period_start: str = Field(description="Start of the current spend period, inclusive.")
    period_end: str = Field(description="End of the current spend period, exclusive.")
    committed: float = Field(
        description="Total of your placed, approved and pending-approval orders in the period."
    )
    remaining: float = Field(description="periodSpendCap minus committed, at least 0.")


class Mandate(CamelModel):
    id: str
    version: int = Field(
        description="Increments on every edit; quotes and orders record the version they "
        "were judged against."
    )
    agent: MandateAgent
    buyer_organisation: MandateBuyerOrganisation
    currency: Literal["EUR"] = Field(
        default="EUR", description="Every amount is in this currency, excluding VAT."
    )

    # Spend
    max_order_total: float = Field(description="Maximum total of one order.")
    period_spend_cap: float = Field(
        description="Maximum your orders may commit in one spend period."
    )
    spend_period: Literal["WEEK", "MONTH"] = Field(
        description="WEEK runs Monday to Sunday, MONTH a calendar month, both in "
        "Europe/Helsinki time."
    )
    category_spend_caps: list[CategorySpendCap] = Field(
        description="Maximum per category per spend period."
    )

    # Assortment
    allowed_category_codes: list[str] = Field(description="Empty allows every category.")
    blocked_category_codes: list[str]
    allowed_vendors: list[str] = Field(description="Vendor names; empty allows every vendor.")
    blocked_vendors: list[str]
    allowed_countries_of_origin: list[str] = Field(
        description="ISO 3166-1 alpha-2, lowercase; empty allows every origin."
    )

    # Requirements
    required_claims: list[Claim] = Field(description="Every product must carry all of these.")
    required_labels: list[str] = Field(description="Every product must carry all of these.")
    required_diets: list[str] = Field(description="Every product must carry all of these.")
    excluded_allergens: list[str] = Field(description="GS1 allergen codes.")
    allergen_strictness: Literal["contains", "may_contain", "declared_free"] = Field(
        description="contains: a product declared CONTAINS is excluded; may_contain: "
        "MAY_CONTAIN too; declared_free: only products declared FREE_FROM every excluded "
        "allergen are allowed."
    )

    # Substitution
    substitution_policy: Literal["NEVER", "IF_REQUIREMENTS_HOLD", "ALWAYS_NEEDS_APPROVAL"]
    max_substitute_price_increase_pct: float = Field(
        description="How much more a substitute may cost than the product it replaces, in %."
    )

    # Delivery
    later_delivery_needs_approval: bool = Field(
        description="A delivery later than requested needs a human."
    )
    min_delivery_reliability: float | None = Field(
        description="0-1; products below it, or without delivery history, need a human. "
        "null = no minimum."
    )

    # Approval
    auto_approve_up_to: float = Field(
        description="A compliant order below this total needs no human; at most maxOrderTotal."
    )

    period_spend: PeriodSpend
