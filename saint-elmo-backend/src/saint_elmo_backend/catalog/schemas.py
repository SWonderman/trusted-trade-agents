from datetime import date
from typing import Any, Literal

from pydantic import Field

from saint_elmo_backend.catalog.dtos import (
    CatalogProvenance,
    ProductDetail,
    ProductSearchHit,
    ProductSearchResult,
)
from saint_elmo_backend.catalog.enums import (
    AllergenContainment,
    FishProductionMethod,
    Language,
    PackagingLevel,
    SafetyStatementType,
)
from saint_elmo_backend.catalog.models import Product
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


class ProductSummary(CamelBaseModel):
    """
    Fields shared by a search hit and the product detail.
    """

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

    @staticmethod
    def summary_fields(product: Product, name: str | None) -> dict[str, Any]:
        return {
            "code": product.code,
            "name": name,
            "gtin": product.gtin,
            "category_code": product.category.code,
            "vendor": product.vendor.name,
            "brand": product.brand.name if product.brand else None,
            "sales_unit": product.sales_unit,
            "base_unit": product.base_unit,
            "allowed_lot_size": product.allowed_lot_size,
            "units": [
                ProductUnit(
                    code=unit.unit_code,
                    size_in_base_units=unit.size_in_base_units,
                    gtin=unit.gtin,
                )
                for unit in product.units
            ],
            "variable_unit": product.variable_unit,
            "has_deposit": bool(product.deposits),
            "claims": [
                Claim(type=claim.claim_type_code, element=claim.claim_element_code)
                for claim in product.claims
            ],
            "diets": [diet.diet_code for diet in product.diets],
            "labels": [label.label_code for label in product.labels],
            "country_of_origin": product.country_of_origin,
            "delivery_reliability": product.delivery_reliability,
            "carbon_footprint": (
                CarbonFootprint(value=product.carbon_footprint)
                if product.carbon_footprint is not None
                else None
            ),
        }


class ProductHit(ProductSummary):
    relevance: float | None = Field(
        description="Search score in [0, 1], higher is better: full-text matches score "
        "at least 0.5, typo-tolerant name matches below it; null when there was no query"
    )

    @classmethod
    def from_hit(cls, hit: ProductSearchHit) -> "ProductHit":
        return cls(**cls.summary_fields(hit.product, hit.name), relevance=hit.relevance)


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


class Allergen(CamelBaseModel):
    code: str = Field(description="GS1 allergen type, e.g. AM milk")
    name: str | None = Field(description="GS1 name of the allergen code")
    containment: AllergenContainment = Field(
        description="An allergen missing from the list has unknown status, never FREE_FROM"
    )


class Translation(CamelBaseModel):
    """
    Texts of the product in one language; not every language carries every text.
    """

    language: str = Field(description="ISO 639-1")
    name: str | None
    marketing_text: str | None
    key_ingredients: str | None
    additional_description: str | None = Field(description="e.g. contents of a multipack")
    storage_instructions: str | None
    usage_instructions: str | None
    preparation_instructions: str | None
    disposal_information: str | None


class Nutrient(CamelBaseModel):
    code: str = Field(description="GS1 nutrient type, e.g. FAT, ENER-, LACS (lactose)")
    value: DecimalNumber
    unit: str = Field(description="GS1 measurement unit, e.g. GRM, KJO")
    precision: str | None = Field(description="e.g. APPROXIMATELY, LESS_THAN")
    basis_quantity: DecimalNumber | None = Field(
        description="The value is per this quantity, usually 100; null when not declared"
    )
    basis_unit: str | None
    daily_value_percent: DecimalNumber | None
    serving_size: DecimalNumber | None
    serving_size_unit: str | None


class IngredientOrigin(CamelBaseModel):
    stage: str = Field(description="GS1 production stage, e.g. FARMING, MILKING")
    country: str = Field(description="ISO 3166-1 numeric, or NON_EU")


class Ingredient(CamelBaseModel):
    sequence: int = Field(description="Position in the ingredient list, from 1")
    percentage: DecimalNumber | None
    names: dict[str, str] = Field(description="Name per ISO 639-1 language")
    origins: list[IngredientOrigin]


class PackagingLevelDimensions(CamelBaseModel):
    level: PackagingLevel
    length_mm: DecimalNumber | None
    width_mm: DecimalNumber | None
    height_mm: DecimalNumber | None
    gross_weight_g: DecimalNumber | None
    net_weight_g: DecimalNumber | None
    volume_value: DecimalNumber | None
    volume_unit: str | None = Field(
        description="As declared by the manufacturer: may be a volume, weight or count unit"
    )


class Deposit(CamelBaseModel):
    material_code: str = Field(description="Deposit material code; not a catalogue product")
    quantity: DecimalNumber = Field(description="Deposit units per sales unit")
    unit: str


class Producer(CamelBaseModel):
    name: str
    gln: str = Field(description="GS1 Global Location Number of the manufacturer")


class CatchMethod(CamelBaseModel):
    production_method: FishProductionMethod
    method_codes: list[str] = Field(description="GS1 CatchMethodCode, e.g. TM midwater trawls")
    area_codes: list[str] = Field(description="GS1 CatchAreaCode (FAO major fishing areas)")


class FishSpecies(CamelBaseModel):
    species_code: str = Field(description="FAO 3-alpha code, e.g. SAL")
    latin_name: str
    catch_methods: list[CatchMethod]


class SafetyStatement(CamelBaseModel):
    code: str = Field(description="GHS hazard (h) or precautionary (p) statement, e.g. h319")
    type: SafetyStatementType


class SafetySheet(CamelBaseModel):
    sheet_id: str
    statements: list[SafetyStatement]


class CuratedSubstitute(CamelBaseModel):
    code: str
    name: str | None


class ProductDetailResponse(ProductSummary):
    allergens: list[Allergen]
    translations: list[Translation]
    nutrients: list[Nutrient]
    ingredients: list[Ingredient] = Field(description="In ingredient list order")
    packaging_levels: list[PackagingLevelDimensions] = Field(
        description="Manufacturer-declared dimensions and weights, in mm and grams"
    )
    deposits: list[Deposit]
    producers: list[Producer]
    fish_species: list[FishSpecies]
    safety_sheets: list[SafetySheet]
    curated_substitutes: list[CuratedSubstitute] = Field(
        description="Curated substitutes: replacements Valio Aimo itself lists for this product"
    )
    provenance: Provenance

    @classmethod
    def from_detail(cls, detail: ProductDetail) -> "ProductDetailResponse":
        product = detail.product
        return cls(
            **cls.summary_fields(product, detail.name),
            allergens=[
                Allergen(
                    code=allergen.allergen_code,
                    name=allergen.allergen.name,
                    containment=allergen.containment,
                )
                for allergen in sorted(product.allergens, key=lambda a: a.allergen_code)
            ],
            translations=[
                Translation(
                    language=t.language,
                    name=t.name,
                    marketing_text=t.marketing_text,
                    key_ingredients=t.key_ingredients,
                    additional_description=t.additional_description,
                    storage_instructions=t.storage_instructions,
                    usage_instructions=t.usage_instructions,
                    preparation_instructions=t.preparation_instructions,
                    disposal_information=t.disposal_information,
                )
                for t in sorted(product.translations, key=lambda t: t.language)
            ],
            nutrients=[
                Nutrient(
                    code=n.nutrient_code,
                    value=n.value,
                    unit=n.unit,
                    precision=n.precision,
                    basis_quantity=n.basis_quantity,
                    basis_unit=n.basis_unit,
                    daily_value_percent=n.daily_value_percent,
                    serving_size=n.serving_size,
                    serving_size_unit=n.serving_size_unit,
                )
                for n in sorted(product.nutrients, key=lambda n: n.nutrient_code)
            ],
            ingredients=[
                Ingredient(
                    sequence=i.sequence,
                    percentage=i.percentage,
                    names=i.names,
                    origins=[IngredientOrigin(stage=o.stage, country=o.country) for o in i.origins],
                )
                for i in product.ingredients
            ],
            packaging_levels=[
                PackagingLevelDimensions(
                    level=p.level,
                    length_mm=p.length_mm,
                    width_mm=p.width_mm,
                    height_mm=p.height_mm,
                    gross_weight_g=p.gross_weight_g,
                    net_weight_g=p.net_weight_g,
                    volume_value=p.volume_value,
                    volume_unit=p.volume_unit,
                )
                for p in sorted(
                    product.packaging_levels, key=lambda p: list(PackagingLevel).index(p.level)
                )
            ],
            deposits=[
                Deposit(material_code=d.material_code, quantity=d.quantity, unit=d.unit)
                for d in sorted(product.deposits, key=lambda d: d.material_code)
            ],
            producers=[Producer(name=p.name, gln=p.gln) for p in product.producers],
            fish_species=[
                FishSpecies(
                    species_code=f.species_code,
                    latin_name=f.latin_name,
                    catch_methods=[
                        CatchMethod(
                            production_method=m.production_method,
                            method_codes=m.method_codes,
                            area_codes=m.area_codes,
                        )
                        for m in f.catch_methods
                    ],
                )
                for f in sorted(product.fish_species, key=lambda f: f.species_code)
            ],
            safety_sheets=[
                SafetySheet(
                    sheet_id=sheet.sheet_id,
                    statements=[
                        SafetyStatement(code=st.code, type=st.type)
                        for st in sorted(sheet.statements, key=lambda st: st.code)
                    ],
                )
                for sheet in sorted(product.safety_sheets, key=lambda sheet: sheet.sheet_id)
            ],
            curated_substitutes=[
                CuratedSubstitute(code=s.code, name=s.name) for s in detail.curated_substitutes
            ],
            provenance=Provenance.from_provenance(detail.provenance),
        )
