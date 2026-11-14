"""
Static Valio Aimo product data as published (`valio_aimo_junction26_product_data.json`
and the two CSVs), plus the rules that normalize it into the catalogue model.
"""

import csv
import re

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, TypeAdapter
from pydantic.alias_generators import to_camel

from saint_elmo_backend.catalog.enums import (
    AllergenContainment,
    FishProductionMethod,
    PackagingLevel,
    SafetyStatementType,
    VatCode,
)

PRODUCT_DATA_FILE = "valio_aimo_junction26_product_data.json"
DELIVERY_RELIABILITY_FILE = "valio_aimo_junction26_delivery_reliability.csv"
CARBON_FOOTPRINT_FILE = "valio_aimo_junction26_carbon_footprint.csv"


class _SourceModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, frozen=True)


class LocalizedText(_SourceModel):
    language: str
    value: str


class Measure(_SourceModel):
    unit: str
    value: Decimal


class ClassificationValue(_SourceModel):
    id: str
    synkka_id: str | None = None
    unit: str | None = None
    value: Decimal | None = None


class Classification(_SourceModel):
    name: str
    type: str
    values: list[ClassificationValue]


class IngredientOriginSource(_SourceModel):
    country: str
    type: str


class IngredientSource(_SourceModel):
    sequence: int
    percentage: Decimal | None = None
    names: list[LocalizedText] = []
    origins: list[IngredientOriginSource] = []


class NutrientSource(_SourceModel):
    id: str
    value: Decimal
    unit: str
    basis_quantity: Decimal
    basis_quantity_unit: str
    unit_precision: str | None = None
    daily_value_intake_percent: Decimal | None = None
    serving_size: Decimal | None = None
    serving_size_unit: str | None = None


class UnitConversion(_SourceModel):
    synkka_packaging_type: PackagingLevel
    gross_weight: Measure
    height: Measure
    length: Measure
    width: Measure
    net_weight: Measure | None = None
    volume: Measure | None = None


class Media(_SourceModel):
    id: int
    primary: bool


class ProducerSource(_SourceModel):
    id: str
    name: str


class CatchMethod(_SourceModel):
    areas: list[str]
    methods: list[str]
    production_method: str


class FishingReport(_SourceModel):
    id: str
    name: str
    catch_methods: list[CatchMethod]


class SafetyStatementSource(_SourceModel):
    id: str
    type: str


class SafetyData(_SourceModel):
    sheet_id: str
    values: list[SafetyStatementSource]


class SynkkaData(_SourceModel):
    names: list[LocalizedText]
    classifications: list[Classification]
    key_ingredients: list[LocalizedText]
    marketing_texts: list[LocalizedText]
    material_additional_descriptions: list[LocalizedText]
    medias: list[Media]
    nutritional_content: list[NutrientSource]

    brand: str | None = None
    gtin: str | None = None
    last_updated: datetime | None = None
    medias_last_updated: datetime | None = None
    variable_unit: bool | None = None
    vat_code: str | None = None
    min_temperature: Decimal | None = None
    max_temperature: Decimal | None = None
    countries_of_origin: list[str] = []
    producers: list[ProducerSource] = []
    ingredients: list[IngredientSource] = []
    unit_conversions: list[UnitConversion] = []
    storage_instructions: list[LocalizedText] = []
    usage_instructions: list[LocalizedText] = []
    preparation_instructions: list[LocalizedText] = []
    disposal_informations: list[LocalizedText] = []
    fishing_reports: list[FishingReport] = []
    safety_data: list[SafetyData] = []


class UnitSource(_SourceModel):
    unit_id: str
    size_in_base_units: Decimal
    gtin: str | None = None


class DepositSource(_SourceModel):
    material: str
    quantity: Decimal
    unit: str


class SubstitutionSource(_SourceModel):
    product: str
    substitute_product: str


class SourceProduct(_SourceModel):
    id: str
    sales_unit: str
    base_unit: str
    category: str
    allowed_lot_size: Decimal
    deleted: bool
    vendor_name: str
    synkka_data: SynkkaData
    units: list[UnitSource]
    deposits: list[DepositSource]

    sales_unit_gtin: str | None = None
    country_of_origin: str | None = None
    temperature_condition: int | None = None
    substitutions: list[SubstitutionSource] = []


_products_adapter = TypeAdapter(list[SourceProduct])


def load_products(data_dir: Path) -> list[SourceProduct]:
    return _products_adapter.validate_json((data_dir / PRODUCT_DATA_FILE).read_bytes())


def load_product_values(path: Path) -> dict[str, Decimal]:
    """
    Read a two-column `productId,<value>` CSV into {product code: value}.
    """
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        return {row[0]: Decimal(row[1]) for row in reader if row and row[1]}


# --- Normalisation rules ---------------------------------------------------------


def normalize_vat_code(raw: str | None) -> VatCode | None:
    """
    The source has repeated tokens ("MEDIUM MEDIUM") and blanks. A repeat of one valid
    code is that code; mixed codes ("STANDARD MEDIUM") are ambiguous, so None.
    """
    tokens = set((raw or "").split())
    if len(tokens) != 1:
        return None

    (token,) = tokens
    return VatCode(token) if token in VatCode.__members__ else None


# Most cautious first: when a product declares the same allergen twice, the
# riskier statement wins.
_CONTAINMENT_PRECEDENCE = [
    AllergenContainment.CONTAINS,
    AllergenContainment.MAY_CONTAIN,
    AllergenContainment.UNDECLARED,
    AllergenContainment.FREE_FROM,
]


def collect_allergens(synkka: SynkkaData) -> dict[str, AllergenContainment]:
    """
    Merge the `allergen` (CONTAINS / MAY_CONTAIN / UNDECLARED) and `nonAllergen`
    (FREE_FROM) groups into one containment per allergen code.
    """
    found: dict[str, AllergenContainment] = {}
    for group in synkka.classifications:
        if group.name not in ("allergen", "nonAllergen"):
            continue

        for value in group.values:
            containment = AllergenContainment(value.unit)
            current = found.get(value.id)
            if current is None or _CONTAINMENT_PRECEDENCE.index(
                containment
            ) < _CONTAINMENT_PRECEDENCE.index(current):
                found[value.id] = containment

    return found


def collect_codes(synkka: SynkkaData, group_name: str) -> set[str]:
    return {
        value.id
        for group in synkka.classifications
        if group.name == group_name
        for value in group.values
    }


# Synkka files diet types under nutritionalClaim with this pseudo claim type
_DIET_CLAIM_TYPE = "DIET"


def collect_claims(synkka: SynkkaData) -> set[tuple[str, str]]:
    """
    Nutritional claims as GS1 (ClaimTypeCode, ClaimElementCode) pairs. Synkka's own
    value id joins the two (FREE_FROM_LACTOSE); the parts are in `unit` (type) and
    `synkkaId` (element).
    """
    return {
        (value.unit, value.synkka_id)
        for group in synkka.classifications
        if group.name == "nutritionalClaim"
        for value in group.values
        if value.unit and value.synkka_id and value.unit != _DIET_CLAIM_TYPE
    }


def collect_diets(synkka: SynkkaData) -> set[str]:
    """
    GS1 DietTypeCode values, which Synkka carries as claims of type DIET.
    """
    return {
        value.synkka_id
        for group in synkka.classifications
        if group.name == "nutritionalClaim"
        for value in group.values
        if value.unit == _DIET_CLAIM_TYPE and value.synkka_id
    }


# DECIMAL classification groups that repeat nutritionalContent without its basis
_NUTRIENT_GROUPS = ("nutritionFact", "gda", "mineral", "vitamin", "composition")


def collect_nutrients(synkka: SynkkaData) -> list[dict]:
    """
    `nutritionalContent` is the full declaration. The DECIMAL classification groups
    repeat it without a basis quantity; they are used only for nutrients it lacks
    (some products have nothing else).
    """
    rows = [
        {
            "nutrient_code": n.id,
            "value": n.value,
            "unit": n.unit,
            "precision": n.unit_precision,
            "basis_quantity": n.basis_quantity,
            "basis_unit": n.basis_quantity_unit,
            "daily_value_percent": n.daily_value_intake_percent,
            "serving_size": n.serving_size,
            "serving_size_unit": n.serving_size_unit,
        }
        for n in synkka.nutritional_content
    ]

    declared = {n.id for n in synkka.nutritional_content}
    for group in synkka.classifications:
        if group.name not in _NUTRIENT_GROUPS:
            continue

        for value in group.values:
            if value.id in declared or value.value is None or value.unit is None:
                continue
            declared.add(value.id)
            rows.append(
                {
                    "nutrient_code": value.id,
                    "value": value.value,
                    "unit": value.unit,
                    "precision": None,
                    "basis_quantity": None,
                    "basis_unit": None,
                    "daily_value_percent": None,
                    "serving_size": None,
                    "serving_size_unit": None,
                }
            )

    return rows


_TEXT_FIELDS = {
    "name": "names",
    "marketing_text": "marketing_texts",
    "key_ingredients": "key_ingredients",
    "additional_description": "material_additional_descriptions",
    "storage_instructions": "storage_instructions",
    "usage_instructions": "usage_instructions",
    "preparation_instructions": "preparation_instructions",
    "disposal_information": "disposal_informations",
}


def collect_translations(synkka: SynkkaData) -> dict[str, dict[str, str]]:
    """
    Pivot the per-field language lists into {language: {field: text}}. Multiple texts
    for one field and language (multipack contents) are joined line by line.
    """
    texts: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for field, source_field in _TEXT_FIELDS.items():
        for text in getattr(synkka, source_field):
            if value := text.value.strip():
                texts[text.language][field].append(value)

    return {
        language: {field: "\n".join(values) for field, values in fields.items()}
        for language, fields in texts.items()
    }


_TO_MM = {"MMT": Decimal(1), "CMT": Decimal(10)}
_TO_GRAMS = {"GRM": Decimal(1), "KGM": Decimal(1000)}


def to_mm(measure: Measure | None) -> Decimal | None:
    if measure is None or measure.unit not in _TO_MM:
        return None
    return measure.value * _TO_MM[measure.unit]


def to_grams(measure: Measure | None) -> Decimal | None:
    if measure is None or measure.unit not in _TO_GRAMS:
        return None
    return measure.value * _TO_GRAMS[measure.unit]


def normalize_production_method(raw: str) -> FishProductionMethod:
    """
    The source has stray suffixes such as "MARINE_FISHERY1".
    """
    return FishProductionMethod(re.sub(r"\d+$", "", raw))


def normalize_statement_type(raw: str) -> SafetyStatementType:
    """
    "HazardStatement" -> HAZARD, "PrecautionaryStatement" -> PRECAUTIONARY.
    """
    return SafetyStatementType(raw.removesuffix("Statement").upper())
