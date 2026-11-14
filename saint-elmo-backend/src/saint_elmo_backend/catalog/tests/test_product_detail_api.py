"""
GET /api/v1/products/{code}, exercised over HTTP.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.catalog.enums import (
    AllergenContainment,
    FishProductionMethod,
    PackagingLevel,
    SafetyStatementType,
)
from saint_elmo_backend.catalog.models import (
    FishCatchMethod,
    IngredientOrigin,
    Producer,
    ProductFishSpecies,
    ProductIngredient,
    ProductNutrient,
    ProductPackagingLevel,
    ProductSafetySheet,
    ProductSubstitution,
    SafetyStatement,
)
from saint_elmo_backend.catalog.tests.factories import make_product
from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.db.engine import get_engine


def detail_url(code: str) -> str:
    return f"/api/v1/products/{code}"


async def test_detail_carries_the_search_summary_and_provenance(reference_data, session, client):
    await make_product(
        session,
        code="100001",
        names={"en": "Lactose free milk"},
        gtin="06408430000012",
        category="C200",
        vendor="Valio Oy",
        brand="Valio",
        sales_unit="KI",
        base_unit="ST",
        allowed_lot_size=Decimal("1"),
        units={"ST": Decimal("1"), "KI": Decimal("12")},
        claims=[("FREE_FROM", "LACTOSE")],
        diets=["VEGAN"],
        labels=["EU_ORGANIC_FARMING"],
        variable_unit=False,
        country_of_origin="fi",
        delivery_reliability=Decimal("0.975"),
        carbon_footprint=Decimal("1.250"),
    )
    await session.commit()

    response = await client.get(detail_url("100001"))

    assert response.status_code == 200
    body = response.json()
    expected = {
        "code": "100001",
        "name": "Lactose free milk",
        "gtin": "06408430000012",
        "categoryCode": "C200",
        "vendor": "Valio Oy",
        "brand": "Valio",
        "salesUnit": "KI",
        "baseUnit": "ST",
        "allowedLotSize": 1.0,
        "variableUnit": False,
        "hasDeposit": False,
        "claims": [{"type": "FREE_FROM", "element": "LACTOSE"}],
        "diets": ["VEGAN"],
        "labels": ["EU_ORGANIC_FARMING"],
        "countryOfOrigin": "fi",
        "deliveryReliability": 0.975,
        "carbonFootprint": {"value": 1.25, "basis": "PRODUCT_GROUP_AVERAGE"},
        "provenance": {
            "source": "Valio Aimo static catalog + GS1 Synkka",
            "catalogSnapshotDate": get_settings().catalog_snapshot_date.isoformat(),
        },
    }
    assert {key: body.get(key) for key in expected} == expected
    assert sorted(unit["code"] for unit in body["units"]) == ["KI", "ST"]
    assert "relevance" not in body


async def test_unknown_code_is_not_found(client):
    response = await client.get(detail_url("does-not-exist"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


async def test_not_found_is_documented_in_openapi(client):
    schema = (await client.get("/openapi.json")).json()

    responses = schema["paths"]["/api/v1/products/{code}"]["get"]["responses"]
    examples = responses["404"]["content"]["application/json"]["examples"]
    assert [example["value"]["error_code"] for example in examples.values()] == [
        "PRODUCT_NOT_FOUND"
    ]


async def test_detail_lists_every_declared_allergen_status(reference_data, session, client):
    await make_product(
        session,
        code="100001",
        allergens={
            "AM": AllergenContainment.CONTAINS,
            "AN": AllergenContainment.MAY_CONTAIN,
            "AW": AllergenContainment.FREE_FROM,
            "AE": AllergenContainment.UNDECLARED,
        },
    )
    await session.commit()

    response = await client.get(detail_url("100001"))

    allergens = response.json()["allergens"]
    assert [(a["code"], a["containment"]) for a in allergens] == [
        ("AE", "UNDECLARED"),
        ("AM", "CONTAINS"),
        ("AN", "MAY_CONTAIN"),
        ("AW", "FREE_FROM"),
    ]
    assert allergens[1]["name"] == "Milk and its derivatives"


async def test_detail_returns_the_texts_in_every_available_language(
    reference_data, session, client
):
    await make_product(
        session,
        code="100001",
        names={"fi": "Maito", "sv": "Mjölk"},
        marketing_texts={"fi": "Raikas"},
        texts={
            "fi": {
                "key_ingredients": "maito",
                "additional_description": "6 x 1 l",
                "storage_instructions": "Säilytä kylmässä",
                "usage_instructions": "Ravista",
                "preparation_instructions": "Lämmitä",
                "disposal_information": "Kartonki",
            },
            "en": {"key_ingredients": "milk"},
        },
    )
    await session.commit()

    response = await client.get(detail_url("100001"))

    assert response.json()["translations"] == [
        {
            "language": "en",
            "name": None,
            "marketingText": None,
            "keyIngredients": "milk",
            "additionalDescription": None,
            "storageInstructions": None,
            "usageInstructions": None,
            "preparationInstructions": None,
            "disposalInformation": None,
        },
        {
            "language": "fi",
            "name": "Maito",
            "marketingText": "Raikas",
            "keyIngredients": "maito",
            "additionalDescription": "6 x 1 l",
            "storageInstructions": "Säilytä kylmässä",
            "usageInstructions": "Ravista",
            "preparationInstructions": "Lämmitä",
            "disposalInformation": "Kartonki",
        },
        {
            "language": "sv",
            "name": "Mjölk",
            "marketingText": None,
            "keyIngredients": None,
            "additionalDescription": None,
            "storageInstructions": None,
            "usageInstructions": None,
            "preparationInstructions": None,
            "disposalInformation": None,
        },
    ]


async def test_detail_carries_the_nutrients(reference_data, session, client):
    await make_product(
        session,
        code="100001",
        nutrients=[
            ProductNutrient(
                nutrient_code="FAT",
                value=Decimal("1.5"),
                unit="GRM",
                precision="APPROXIMATELY",
                basis_quantity=Decimal("100"),
                basis_unit="MLT",
                daily_value_percent=Decimal("2.14"),
                serving_size=Decimal("200"),
                serving_size_unit="MLT",
            ),
            ProductNutrient(nutrient_code="ENER-", value=Decimal("190"), unit="KJO"),
        ],
    )
    await session.commit()

    response = await client.get(detail_url("100001"))

    assert response.json()["nutrients"] == [
        {
            "code": "ENER-",
            "value": 190.0,
            "unit": "KJO",
            "precision": None,
            "basisQuantity": None,
            "basisUnit": None,
            "dailyValuePercent": None,
            "servingSize": None,
            "servingSizeUnit": None,
        },
        {
            "code": "FAT",
            "value": 1.5,
            "unit": "GRM",
            "precision": "APPROXIMATELY",
            "basisQuantity": 100.0,
            "basisUnit": "MLT",
            "dailyValuePercent": 2.14,
            "servingSize": 200.0,
            "servingSizeUnit": "MLT",
        },
    ]


async def test_detail_lists_ingredients_in_sequence_with_their_origins(
    reference_data, session, client
):
    await make_product(
        session,
        code="100001",
        ingredients=[
            ProductIngredient(sequence=2, percentage=None, names={"fi": "suola", "en": "salt"}),
            ProductIngredient(
                sequence=1,
                percentage=Decimal("98.5"),
                names={"fi": "maito", "en": "milk"},
                origins=[
                    IngredientOrigin(stage="MILKING", country="246"),
                    IngredientOrigin(stage="LAST_PROCESSING", country="246"),
                ],
            ),
        ],
    )
    await session.commit()

    response = await client.get(detail_url("100001"))

    ingredients = response.json()["ingredients"]
    assert [(i["sequence"], i["percentage"], i["names"]) for i in ingredients] == [
        (1, 98.5, {"fi": "maito", "en": "milk"}),
        (2, None, {"fi": "suola", "en": "salt"}),
    ]
    assert sorted(ingredients[0]["origins"], key=lambda o: o["stage"]) == [
        {"stage": "LAST_PROCESSING", "country": "246"},
        {"stage": "MILKING", "country": "246"},
    ]
    assert ingredients[1]["origins"] == []


async def test_detail_carries_packaging_deposits_and_producers(reference_data, session, client):
    await make_product(
        session,
        code="100001",
        deposits=["PANT1"],
        packaging_levels=[
            ProductPackagingLevel(
                level=PackagingLevel.CASE,
                length_mm=Decimal("300"),
                width_mm=Decimal("200"),
                height_mm=Decimal("250.5"),
                gross_weight_g=Decimal("12500"),
                net_weight_g=Decimal("12000"),
                volume_value=Decimal("12"),
                volume_unit="LTR",
            ),
        ],
        producers=[Producer(gln="6410000000001", name="Valio Oy")],
    )
    await session.commit()

    response = await client.get(detail_url("100001"))

    body = response.json()
    assert body["packagingLevels"] == [
        {
            "level": "CASE",
            "lengthMm": 300.0,
            "widthMm": 200.0,
            "heightMm": 250.5,
            "grossWeightG": 12500.0,
            "netWeightG": 12000.0,
            "volumeValue": 12.0,
            "volumeUnit": "LTR",
        }
    ]
    assert body["deposits"] == [{"materialCode": "PANT1", "quantity": 1.0, "unit": "ST"}]
    assert body["producers"] == [{"name": "Valio Oy", "gln": "6410000000001"}]


async def test_detail_carries_fish_species_with_catch_methods(reference_data, session, client):
    await make_product(
        session,
        code="100001",
        fish_species=[
            ProductFishSpecies(
                species_code="SAL",
                latin_name="Salmo salar",
                catch_methods=[
                    FishCatchMethod(
                        production_method=FishProductionMethod.AQUACULTURE,
                        method_codes=[],
                        area_codes=["27"],
                    ),
                    FishCatchMethod(
                        production_method=FishProductionMethod.MARINE_FISHERY,
                        method_codes=["TM"],
                        area_codes=["27", "21"],
                    ),
                ],
            )
        ],
    )
    await session.commit()

    response = await client.get(detail_url("100001"))

    [species] = response.json()["fishSpecies"]
    assert species["speciesCode"] == "SAL"
    assert species["latinName"] == "Salmo salar"
    assert sorted(species["catchMethods"], key=lambda m: m["productionMethod"]) == [
        {"productionMethod": "AQUACULTURE", "methodCodes": [], "areaCodes": ["27"]},
        {"productionMethod": "MARINE_FISHERY", "methodCodes": ["TM"], "areaCodes": ["27", "21"]},
    ]


async def test_detail_carries_safety_sheet_statements(reference_data, session, client):
    await make_product(
        session,
        code="100001",
        safety_sheets=[
            ProductSafetySheet(
                sheet_id="SDS-1",
                statements=[
                    SafetyStatement(code="p102", type=SafetyStatementType.PRECAUTIONARY),
                    SafetyStatement(code="h319", type=SafetyStatementType.HAZARD),
                ],
            )
        ],
    )
    await session.commit()

    response = await client.get(detail_url("100001"))

    assert response.json()["safetySheets"] == [
        {
            "sheetId": "SDS-1",
            "statements": [
                {"code": "h319", "type": "HAZARD"},
                {"code": "p102", "type": "PRECAUTIONARY"},
            ],
        }
    ]


async def test_detail_lists_curated_substitutes_by_code_and_name(reference_data, session, client):
    oat = await make_product(session, code="200002", names={"en": "Oat drink", "fi": "Kaurajuoma"})
    soy = await make_product(session, code="200001", names={"fi": "Soijajuoma"})
    await make_product(
        session,
        code="100001",
        substitutions=[ProductSubstitution(substitute=oat), ProductSubstitution(substitute=soy)],
    )
    await session.commit()

    response = await client.get(detail_url("100001"), params={"language": "en"})

    assert response.json()["curatedSubstitutes"] == [
        {"code": "200001", "name": "Soijajuoma"},
        {"code": "200002", "name": "Oat drink"},
    ]


async def test_sparse_product_returns_empty_sections(reference_data, session, client):
    await make_product(session, code="100001", names={"fi": "Maito"})
    await session.commit()

    response = await client.get(detail_url("100001"))

    assert response.status_code == 200
    body = response.json()
    for section in (
        "allergens",
        "nutrients",
        "ingredients",
        "packagingLevels",
        "deposits",
        "producers",
        "fishSpecies",
        "safetySheets",
        "curatedSubstitutes",
    ):
        assert body[section] == [], section
    for field in ("gtin", "brand", "countryOfOrigin", "deliveryReliability", "carbonFootprint"):
        assert body[field] is None, field


@contextmanager
def recorded_statements() -> Iterator[list[str]]:
    """
    SQL statements the app's engine executes inside the block.
    """
    statements: list[str] = []
    engine = get_engine().sync_engine

    def record(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", record)


async def make_populated_product(session: AsyncSession, code: str, rows: int) -> None:
    """
    A product with `rows` entries in every list section, nested ones included.
    """
    substitutes = [
        await make_product(session, code=f"{code}-S{i}", names={"en": f"Sub {i}"})
        for i in range(rows)
    ]
    allergen_codes = ["AM", "AN", "AW"][:rows]
    await make_product(
        session,
        code=code,
        names={"fi": "Maito", "sv": "Mjölk", "en": "Milk"},
        deposits=[f"PANT{i}" for i in range(rows)],
        allergens={c: AllergenContainment.CONTAINS for c in allergen_codes},
        nutrients=[
            ProductNutrient(nutrient_code=c, value=Decimal("1"), unit="GRM")
            for c in ["FAT", "ENER-", "PRO-"][:rows]
        ],
        ingredients=[
            ProductIngredient(
                sequence=i + 1,
                names={"fi": f"aine {i}"},
                origins=[
                    IngredientOrigin(stage="FARMING", country=str(246 + j)) for j in range(rows)
                ],
            )
            for i in range(rows)
        ],
        packaging_levels=[
            ProductPackagingLevel(level=level) for level in list(PackagingLevel)[:rows]
        ],
        producers=[Producer(gln=f"{code}{i}".ljust(13, "0"), name=f"P{i}") for i in range(rows)],
        fish_species=[
            ProductFishSpecies(
                species_code=f"F{i}",
                latin_name=f"Fish {i}",
                catch_methods=[
                    FishCatchMethod(
                        production_method=FishProductionMethod.AQUACULTURE,
                        method_codes=[],
                        area_codes=[],
                    )
                    for _ in range(rows)
                ],
            )
            for i in range(rows)
        ],
        safety_sheets=[
            ProductSafetySheet(
                sheet_id=f"SDS-{i}",
                statements=[
                    SafetyStatement(code=f"h{j}", type=SafetyStatementType.HAZARD)
                    for j in range(rows)
                ],
            )
            for i in range(rows)
        ],
        substitutions=[ProductSubstitution(substitute=sub) for sub in substitutes],
    )


async def test_loading_a_product_does_not_query_per_related_row(reference_data, session, client):
    await make_populated_product(session, "1", rows=1)
    await make_populated_product(session, "3", rows=3)
    await session.commit()

    with recorded_statements() as one_row:
        assert (await client.get(detail_url("1"))).status_code == 200
    with recorded_statements() as three_rows:
        response = await client.get(detail_url("3"))

    body = response.json()
    for section in (
        "allergens",
        "nutrients",
        "ingredients",
        "packagingLevels",
        "deposits",
        "producers",
        "fishSpecies",
        "safetySheets",
        "curatedSubstitutes",
    ):
        assert len(body[section]) == 3, section
    assert len(three_rows) == len(one_row)


async def test_detail_response_is_documented_in_openapi(client):
    schema = (await client.get("/openapi.json")).json()

    operation = schema["paths"]["/api/v1/products/{code}"]["get"]
    ok = operation["responses"]["200"]
    response_ref = ok["content"]["application/json"]["schema"]["$ref"]
    properties = schema["components"]["schemas"][response_ref.rsplit("/", 1)[-1]]["properties"]

    assert {
        "allergens",
        "translations",
        "nutrients",
        "ingredients",
        "packagingLevels",
        "deposits",
        "producers",
        "fishSpecies",
        "safetySheets",
        "curatedSubstitutes",
        "provenance",
    } <= set(properties)
    assert "relevance" not in properties
    assert [p["name"] for p in operation["parameters"]] == ["code", "language"]
