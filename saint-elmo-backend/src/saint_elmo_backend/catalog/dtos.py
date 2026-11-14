from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from saint_elmo_backend.catalog.models import Product


@dataclass(frozen=True, slots=True)
class CatalogProvenance:
    source: str
    catalog_snapshot_date: date


@dataclass(frozen=True, slots=True)
class ProductFilters:
    """
    Structured search filters, ANDed together. An empty tuple or None leaves that
    attribute unfiltered.
    """

    category_codes: tuple[str, ...] = ()
    vendors: tuple[str, ...] = ()
    # (claim type, claim element) pairs; a product must carry all of them
    required_claims: tuple[tuple[str, str], ...] = ()
    required_diets: tuple[str, ...] = ()
    required_labels: tuple[str, ...] = ()
    # ISO 3166-1 alpha-2, lowercase; a product must come from any of them
    countries_of_origin: tuple[str, ...] = ()
    # Products without reliability data never pass this filter
    min_delivery_reliability: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ProductMatch:
    product: "Product"
    relevance: float | None


@dataclass(frozen=True, slots=True)
class ProductSearchHit:
    product: "Product"
    name: str | None
    relevance: float | None


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
class CategoryUsage:
    code: str
    product_count: int


@dataclass(frozen=True, slots=True)
class CatalogVocabulary:
    claims: list[ClaimUsage]
    diets: list[CodeUsage]
    labels: list[CodeUsage]
    allergens: list[CodeUsage]
    categories: list[CategoryUsage]
