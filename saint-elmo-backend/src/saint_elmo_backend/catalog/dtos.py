from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from saint_elmo_backend.catalog.enums import (
    AllergenContainment,
    AllergenStatus,
    AllergenStrictness,
)

if TYPE_CHECKING:
    from saint_elmo_backend.catalog.models import Product


@dataclass(frozen=True, slots=True)
class CatalogProvenance:
    source: str
    catalog_snapshot_date: date


@dataclass(frozen=True, slots=True)
class ClaimCode:
    """
    A GS1 claim: a claim type and the element it is about, e.g. FREE_FROM + LACTOSE.
    """

    type: str
    element: str


@dataclass(frozen=True, slots=True)
class ProductFilters:
    """
    Structured search filters, ANDed together. An empty tuple or None leaves that
    attribute unfiltered.
    """

    category_codes: tuple[str, ...] = ()
    vendors: tuple[str, ...] = ()
    # A product must carry all of them
    required_claims: tuple[ClaimCode, ...] = ()
    required_diets: tuple[str, ...] = ()
    required_labels: tuple[str, ...] = ()
    # ISO 3166-1 alpha-2, lowercase; a product must come from any of them
    countries_of_origin: tuple[str, ...] = ()
    # Products without reliability data never pass this filter
    min_delivery_reliability: Decimal | None = None
    # GS1 allergen codes; how strictly they are excluded is set by allergen_strictness
    excluded_allergens: tuple[str, ...] = ()
    allergen_strictness: AllergenStrictness = AllergenStrictness.CONTAINS


@dataclass(frozen=True, slots=True)
class ProductMatch:
    product: "Product"
    relevance: float | None


@dataclass(frozen=True, slots=True)
class HitAllergen:
    code: str
    status: AllergenStatus


@dataclass(frozen=True, slots=True)
class ProductSearchHit:
    product: "Product"
    name: str | None
    relevance: float | None
    allergens: list[HitAllergen]


@dataclass(frozen=True, slots=True)
class ProductSearchResult:
    total: int
    hits: list[ProductSearchHit]
    provenance: CatalogProvenance


@dataclass(frozen=True, slots=True)
class CuratedSubstitute:
    code: str
    name: str | None


@dataclass(frozen=True, slots=True)
class ProductDetail:
    product: "Product"
    name: str | None
    curated_substitutes: list[CuratedSubstitute]
    provenance: CatalogProvenance


@dataclass(frozen=True, slots=True)
class CodeUsage:
    """
    One code of a GS1 code list and how many products use it.
    """

    code: str
    name: str | None
    definition: str | None
    product_count: int


@dataclass(frozen=True, slots=True)
class GS1Code:
    code: str
    name: str | None
    definition: str | None


@dataclass(frozen=True, slots=True)
class ClaimUsage:
    """
    One claim type + element pair and how many products make that claim.
    """

    type: GS1Code
    element: GS1Code
    product_count: int


@dataclass(frozen=True, slots=True)
class AllergenUsage:
    """
    One GS1 allergen code and how many products declare each status for it. A product
    without a row for the allergen has unknown status and is not counted.
    """

    code: str
    name: str | None
    definition: str | None
    status_counts: dict[AllergenContainment, int]

    @property
    def product_count(self) -> int:
        # One row per product and allergen, so the statuses partition the products
        return sum(self.status_counts.values())


@dataclass(frozen=True, slots=True)
class CategoryUsage:
    code: str
    product_count: int


@dataclass(frozen=True, slots=True)
class CatalogVocabulary:
    claims: list[ClaimUsage]
    diets: list[CodeUsage]
    labels: list[CodeUsage]
    allergens: list[AllergenUsage]
    categories: list[CategoryUsage]
