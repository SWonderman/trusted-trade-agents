from decimal import Decimal

import pytest

from saint_elmo_backend.catalog import source
from saint_elmo_backend.catalog.enums import (
    AllergenContainment,
    FishProductionMethod,
    SafetyStatementType,
    VatCode,
)


def _synkka(**fields) -> source.SynkkaData:
    return source.SynkkaData.model_validate(
        {
            "names": [],
            "classifications": [],
            "keyIngredients": [],
            "marketingTexts": [],
            "materialAdditionalDescriptions": [],
            "medias": [],
            "nutritionalContent": [],
            **fields,
        }
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("MEDIUM", VatCode.MEDIUM),
        ("MEDIUM MEDIUM", VatCode.MEDIUM),
        ("STANDARD MEDIUM", None),
        ("", None),
        (None, None),
        ("UNKNOWN", None),
    ],
)
def test_normalize_vat_code(raw, expected):
    assert source.normalize_vat_code(raw) == expected


def test_allergen_groups_merge_into_one_containment_per_code():
    synkka = _synkka(
        classifications=[
            {
                "name": "allergen",
                "type": "ENUM",
                "values": [
                    {"id": "AM", "unit": "CONTAINS"},
                    {"id": "AW", "unit": "MAY_CONTAIN"},
                ],
            },
            {"name": "nonAllergen", "type": "ENUM", "values": [{"id": "AE", "unit": "FREE_FROM"}]},
        ]
    )

    assert source.collect_allergens(synkka) == {
        "AM": AllergenContainment.CONTAINS,
        "AW": AllergenContainment.MAY_CONTAIN,
        "AE": AllergenContainment.FREE_FROM,
    }


def test_conflicting_allergen_declarations_resolve_to_the_riskier_one():
    # Product 468044 declares milk as both CONTAINS and FREE_FROM
    synkka = _synkka(
        classifications=[
            {"name": "nonAllergen", "type": "ENUM", "values": [{"id": "AM", "unit": "FREE_FROM"}]},
            {"name": "allergen", "type": "ENUM", "values": [{"id": "AM", "unit": "CONTAINS"}]},
        ]
    )

    assert source.collect_allergens(synkka) == {"AM": AllergenContainment.CONTAINS}


def test_missing_allergen_data_yields_no_rows():
    # No row means unknown - it must never be read as FREE_FROM
    assert source.collect_allergens(_synkka()) == {}


def test_nutrients_prefer_declaration_and_fill_gaps_from_classifications():
    synkka = _synkka(
        nutritionalContent=[
            {
                "id": "FAT",
                "value": 1.5,
                "unit": "GRM",
                "basisQuantity": 100,
                "basisQuantityUnit": "GRM",
            }
        ],
        classifications=[
            {
                "name": "nutritionFact",
                "type": "DECIMAL",
                "values": [
                    {"id": "FAT", "value": 9.9, "unit": "GRM"},
                    {"id": "LACS", "value": 0, "unit": "GRM"},
                ],
            }
        ],
    )

    rows = {row["nutrient_code"]: row for row in source.collect_nutrients(synkka)}

    assert rows["FAT"]["value"] == Decimal("1.5")
    assert rows["FAT"]["basis_quantity"] == Decimal(100)
    assert rows["LACS"]["value"] == Decimal(0)
    assert rows["LACS"]["basis_quantity"] is None


def test_translations_pivot_by_language_and_join_repeated_texts():
    synkka = _synkka(
        names=[
            {"language": "en", "value": "Milk 1 l"},
            {"language": "fi", "value": "Maito 1 l"},
        ],
        keyIngredients=[{"language": "et", "value": "piim"}],
        materialAdditionalDescriptions=[
            {"language": "en", "value": "Contains: bread A"},
            {"language": "en", "value": "Contains: bread B"},
        ],
    )

    assert source.collect_translations(synkka) == {
        "en": {
            "name": "Milk 1 l",
            "additional_description": "Contains: bread A\nContains: bread B",
        },
        "fi": {"name": "Maito 1 l"},
        "et": {"key_ingredients": "piim"},
    }


@pytest.mark.parametrize(
    ("unit", "value", "mm"),
    [("MMT", "342", Decimal(342)), ("CMT", "34.2", Decimal(342)), ("GRM", "1", None)],
)
def test_to_mm(unit, value, mm):
    assert source.to_mm(source.Measure(unit=unit, value=Decimal(value))) == mm


@pytest.mark.parametrize(
    ("unit", "value", "grams"),
    [("GRM", "500", Decimal(500)), ("KGM", "2.5", Decimal(2500)), ("LTR", "1", None)],
)
def test_to_grams(unit, value, grams):
    assert source.to_grams(source.Measure(unit=unit, value=Decimal(value))) == grams


def test_normalize_production_method_strips_stray_suffix():
    assert source.normalize_production_method("MARINE_FISHERY1") == FishProductionMethod.MARINE_FISHERY
    assert source.normalize_production_method("AQUACULTURE") == FishProductionMethod.AQUACULTURE


def test_normalize_statement_type():
    assert source.normalize_statement_type("HazardStatement") == SafetyStatementType.HAZARD
    assert (
        source.normalize_statement_type("PrecautionaryStatement")
        == SafetyStatementType.PRECAUTIONARY
    )
