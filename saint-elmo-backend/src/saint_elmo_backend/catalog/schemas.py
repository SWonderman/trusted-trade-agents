from datetime import date
from typing import Literal

from pydantic import Field

from saint_elmo_backend.catalog.dtos import (
    CatalogProvenance,
    ProductSearchHit,
    ProductSearchResult,
)
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.core.schema import CamelBaseModel, DecimalNumber


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


class CarbonFootprint(CamelBaseModel):
    value: DecimalNumber = Field(description="kg CO2-eq per kg")
    basis: Literal["PRODUCT_GROUP_AVERAGE"] = Field(
        default="PRODUCT_GROUP_AVERAGE",
        description="The value is the average of the product's group, not of this product",
    )


class ProductUnit(CamelBaseModel):
    code: str
    size_in_base_units: DecimalNumber
    gtin: str | None = Field(description="GTIN of this packaging level, e.g. the case")


class Claim(CamelBaseModel):
    type: str = Field(description="GS1 claim type, e.g. FREE_FROM")
    element: str = Field(description="GS1 claim element, e.g. LACTOSE")


class ProductHit(CamelBaseModel):
    code: str
    name: str | None
    gtin: str | None = Field(
        description="GTIN of the consumer unit, which identifies the product in GS1 data; "
        "each entry in units carries the GTIN of its own packaging level"
    )
    category_code: str = Field(description="Category names are not in the source data")
    vendor: str
    brand: str | None
    sales_unit: str = Field(description="Unit the product is ordered and priced in")
    base_unit: str
    allowed_lot_size: DecimalNumber = Field(
        description="Order quantity must be a multiple of this, in sales units"
    )
    units: list[ProductUnit] = Field(
        description="Units the product can be handled in, converted to base units"
    )
    variable_unit: bool | None = Field(
        description="Sold by variable weight, so the actual quantity of a unit varies"
    )
    has_deposit: bool = Field(
        description="Returnable packaging is charged together with each sales unit"
    )
    claims: list[Claim]
    diets: list[str] = Field(description="GS1 diet codes, e.g. VEGAN")
    labels: list[str] = Field(description="Packaging label codes, e.g. EU_ORGANIC_FARMING")
    country_of_origin: str | None = Field(description="ISO 3166-1 alpha-2, lowercase")
    delivery_reliability: DecimalNumber | None = Field(
        description="Share of historical orders delivered as ordered, 0-1; "
        "null means no history, not unreliable"
    )
    carbon_footprint: CarbonFootprint | None
    relevance: float | None = Field(
        description="Search score in [0, 1], higher is better: full-text matches score "
        "at least 0.5, typo-tolerant name matches below it; null when there was no query"
    )

    @classmethod
    def from_hit(cls, hit: ProductSearchHit) -> "ProductHit":
        product = hit.product
        return cls(
            code=product.code,
            name=hit.name,
            gtin=product.gtin,
            category_code=product.category.code,
            vendor=product.vendor.name,
            brand=product.brand.name if product.brand else None,
            sales_unit=product.sales_unit,
            base_unit=product.base_unit,
            allowed_lot_size=product.allowed_lot_size,
            units=[
                ProductUnit(
                    code=unit.unit_code,
                    size_in_base_units=unit.size_in_base_units,
                    gtin=unit.gtin,
                )
                for unit in product.units
            ],
            variable_unit=product.variable_unit,
            has_deposit=bool(product.deposits),
            claims=[
                Claim(type=claim.claim_type_code, element=claim.claim_element_code)
                for claim in product.claims
            ],
            diets=[diet.diet_code for diet in product.diets],
            labels=[label.label_code for label in product.labels],
            country_of_origin=product.country_of_origin,
            delivery_reliability=product.delivery_reliability,
            carbon_footprint=(
                CarbonFootprint(value=product.carbon_footprint)
                if product.carbon_footprint is not None
                else None
            ),
            relevance=hit.relevance,
        )


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
