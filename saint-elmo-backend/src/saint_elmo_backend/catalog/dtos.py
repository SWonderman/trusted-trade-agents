from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from saint_elmo_backend.catalog.models import Product


@dataclass(frozen=True, slots=True)
class CatalogProvenance:
    source: str
    catalog_snapshot_date: date


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
