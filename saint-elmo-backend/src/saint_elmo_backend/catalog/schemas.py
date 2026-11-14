from datetime import date

from pydantic import Field

from saint_elmo_backend.catalog.dtos import (
    CatalogProvenance,
    ProductSearchHit,
    ProductSearchResult,
)
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.core.schema import CamelBaseModel


class ProductSearchRequest(CamelBaseModel):
    query: str | None = Field(
        default=None,
        description="Free text matched against fi, sv and en names and texts at once",
    )
    language: Language = Field(
        default=Language.EN,
        description="Language of the returned texts; falls back to fi when missing",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class Provenance(CamelBaseModel):
    source: str
    catalog_snapshot_date: date

    @classmethod
    def from_provenance(cls, provenance: CatalogProvenance) -> "Provenance":
        return cls(
            source=provenance.source,
            catalog_snapshot_date=provenance.catalog_snapshot_date,
        )


class ProductHit(CamelBaseModel):
    code: str
    name: str | None
    relevance: float | None = Field(
        description="Text search rank, higher is better; null when there was no query"
    )

    @classmethod
    def from_hit(cls, hit: ProductSearchHit) -> "ProductHit":
        return cls(code=hit.product.code, name=hit.name, relevance=hit.relevance)


class ProductSearchResponse(CamelBaseModel):
    total: int
    items: list[ProductHit]
    provenance: Provenance

    @classmethod
    def from_result(cls, result: ProductSearchResult) -> "ProductSearchResponse":
        return cls(
            total=result.total,
            items=[ProductHit.from_hit(hit) for hit in result.hits],
            provenance=Provenance.from_provenance(result.provenance),
        )
