from datetime import date
from typing import Literal

from pydantic import Field

from saint_elmo_backend.catalog.models import Product
from saint_elmo_backend.core.schema import CamelBaseModel

type Language = Literal["en", "fi", "sv"]


class ProductSearchRequest(CamelBaseModel):
    query: str | None = Field(
        default=None,
        description="Free text matched against fi, sv and en names and texts at once",
    )
    language: Language = Field(
        default="en",
        description="Language of the returned texts; falls back to fi when missing",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class Provenance(CamelBaseModel):
    source: str
    catalog_snapshot_date: date


class ProductHit(CamelBaseModel):
    code: str
    name: str | None

    @classmethod
    def from_product(cls, product: Product, language: Language) -> "ProductHit":
        name = next((t.name for t in product.translations if t.language == language), None)
        return cls(code=product.code, name=name)


class ProductSearchResponse(CamelBaseModel):
    total: int
    items: list[ProductHit]
    provenance: Provenance
