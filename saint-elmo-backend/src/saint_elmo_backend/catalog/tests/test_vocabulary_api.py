"""
GET /api/v1/catalog/vocabulary, exercised over HTTP.
"""

from saint_elmo_backend.catalog.enums import AllergenContainment
from saint_elmo_backend.catalog.models import Category, ClaimElement, Diet
from saint_elmo_backend.catalog.tests.factories import make_product

VOCABULARY_URL = "/api/v1/catalog/vocabulary"

VEGAN_DEFINITION = (
    "Products that are not of animal origin and at no stage of production and processing "
    "has use been made of, or the product been supplemented with ingredients or processing "
    "aids or substances that are of animal origin. The product has not been tested on "
    "animals. Local regulations, where they exist, prevail since the term may be a "
    "combination or all of the above statements."
)
HALAL_DEFINITION = "Denotes selling or serving food ritually fit according to Islamic dietary laws."


async def test_diets_list_only_used_codes_with_product_counts(reference_data, session, client):
    await make_product(session, diets=["VEGAN", "HALAL"])
    await make_product(session, diets=["VEGAN"])
    await make_product(session)
    await session.commit()

    response = await client.get(VOCABULARY_URL)

    assert response.status_code == 200
    assert response.json()["diets"] == [
        {"code": "HALAL", "name": "Halal", "definition": HALAL_DEFINITION, "productCount": 1},
        {"code": "VEGAN", "name": "Vegan", "definition": VEGAN_DEFINITION, "productCount": 2},
    ]


async def test_non_standard_codes_are_listed_with_null_name(reference_data, session, client):
    session.add(Diet(code="LOCAL_DIET", is_standard=False))
    await session.flush()
    await make_product(session, diets=["LOCAL_DIET"])
    await session.commit()

    response = await client.get(VOCABULARY_URL)

    assert response.json()["diets"] == [
        {"code": "LOCAL_DIET", "name": None, "definition": None, "productCount": 1}
    ]


async def test_labels_list_only_used_codes_with_product_counts(reference_data, session, client):
    await make_product(session, labels=["EU_ORGANIC_FARMING"])
    await make_product(session, labels=["EU_ORGANIC_FARMING"])
    await make_product(session, labels=["EU_ORGANIC_FARMING"])
    await session.commit()

    response = await client.get(VOCABULARY_URL)

    assert response.json()["labels"] == [
        {
            "code": "EU_ORGANIC_FARMING",
            "name": "EU Organic Farming",
            "definition": "New EU organic logo the EU introduced a new organic logo to ensure "
            "consumer protection and common standards. See www.organic-farming.europa.eu",
            "productCount": 3,
        }
    ]


async def test_allergens_count_every_product_declaring_any_status(reference_data, session, client):
    await make_product(
        session, allergens={"AM": AllergenContainment.CONTAINS, "AW": AllergenContainment.FREE_FROM}
    )
    await make_product(session, allergens={"AM": AllergenContainment.FREE_FROM})
    await make_product(session)
    await session.commit()

    response = await client.get(VOCABULARY_URL)

    allergens = response.json()["allergens"]
    assert [(a["code"], a["name"], a["productCount"]) for a in allergens] == [
        ("AM", "Milk and its derivatives", 2),
        ("AW", "Cereals and its derivatives", 1),
    ]
    assert allergens[0]["definition"].startswith(
        "Definition (includes Common Name): Refers to the presence of milk"
    )


async def test_claims_list_used_type_element_pairs_with_both_names(reference_data, session, client):
    await make_product(session, claims=[("FREE_FROM", "LACTOSE"), ("LOW", "FAT")])
    await make_product(session, claims=[("FREE_FROM", "LACTOSE")])
    await session.commit()

    response = await client.get(VOCABULARY_URL)

    claims = response.json()["claims"]
    assert [
        (
            claim["type"]["code"],
            claim["type"]["name"],
            claim["element"]["code"],
            claim["element"]["name"],
            claim["productCount"],
        )
        for claim in claims
    ] == [
        ("FREE_FROM", "Free from", "LACTOSE", "Lactose", 2),
        ("LOW", "Low", "FAT", "Fat", 1),
    ]
    assert claims[0]["element"]["definition"] == "Lactose."
    assert claims[0]["type"]["definition"].startswith(
        "A claim that a product is completely free from the substance"
    )


async def test_non_standard_claim_codes_are_listed_with_null_name(reference_data, session, client):
    session.add(ClaimElement(code="LOCAL_ELEMENT", is_standard=False))
    await session.flush()
    await make_product(session, claims=[("FREE_FROM", "LOCAL_ELEMENT")])
    await session.commit()

    response = await client.get(VOCABULARY_URL)

    [claim] = response.json()["claims"]
    assert claim["type"]["code"] == "FREE_FROM"
    assert claim["element"] == {"code": "LOCAL_ELEMENT", "name": None, "definition": None}
    assert claim["productCount"] == 1


async def test_categories_list_used_codes_with_product_counts(reference_data, session, client):
    session.add(Category(code="C999"))
    await make_product(session, category="C200")
    await make_product(session, category="C100")
    await make_product(session, category="C200")
    await session.commit()

    response = await client.get(VOCABULARY_URL)

    assert response.json()["categories"] == [
        {"code": "C100", "productCount": 1},
        {"code": "C200", "productCount": 2},
    ]


async def test_vocabulary_is_documented_in_openapi(client):
    schema = (await client.get("/openapi.json")).json()

    response = schema["paths"]["/api/v1/catalog/vocabulary"]["get"]["responses"]["200"]
    ref = response["content"]["application/json"]["schema"]["$ref"]
    vocabulary = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]
    assert sorted(vocabulary["properties"]) == [
        "allergens",
        "categories",
        "claims",
        "diets",
        "labels",
    ]
