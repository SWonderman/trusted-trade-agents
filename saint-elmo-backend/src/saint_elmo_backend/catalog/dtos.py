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
class ProductSearchHit:
    product: "Product"
    name: str | None


@dataclass(frozen=True, slots=True)
class ProductSearchResult:
    total: int
    hits: list[ProductSearchHit]
    provenance: CatalogProvenance
