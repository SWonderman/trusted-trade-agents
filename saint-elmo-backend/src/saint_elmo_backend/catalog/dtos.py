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
