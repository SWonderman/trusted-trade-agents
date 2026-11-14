"""
POST /api/v1/products/search, exercised over HTTP.
"""

from decimal import Decimal

import pytest

from saint_elmo_backend.catalog.tests.factories import make_product
from saint_elmo_backend.core.settings import get_settings

SEARCH_URL = "/api/v1/products/search"


async def test_browse_returns_products_with_provenance(reference_data, session, client):
    await make_product(session, code="100001", names={"en": "Lactose free milk"})
    await session.commit()

    response = await client.post(SEARCH_URL, json={})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [(item["code"], item["name"]) for item in body["items"]] == [
        ("100001", "Lactose free milk")
    ]
    assert body["provenance"] == {
        "source": "Valio Aimo static catalog + GS1 Synkka",
        "catalogSnapshotDate": get_settings().catalog_snapshot_date.isoformat(),
    }


async def test_browse_returns_most_reliable_products_first(reference_data, session, client):
    await make_product(session, code="100001", delivery_reliability=Decimal("0.40"))
    await make_product(session, code="100002", delivery_reliability=None)
    await make_product(session, code="100003", delivery_reliability=Decimal("0.95"))
    await session.commit()

    response = await client.post(SEARCH_URL, json={})

    assert [item["code"] for item in response.json()["items"]] == [
        "100003",
        "100001",
        "100002",
    ]


async def test_total_counts_every_match_while_items_hold_one_page(
    reference_data, session, client
):
    for code in ("100001", "100002", "100003"):
        await make_product(session, code=code)
    await session.commit()

    response = await client.post(SEARCH_URL, json={"limit": 1, "offset": 1})

    body = response.json()
    assert body["total"] == 3
    assert [item["code"] for item in body["items"]] == ["100002"]


async def test_language_selects_the_returned_name(reference_data, session, client):
    await make_product(
        session, names={"en": "Milk", "fi": "Maito", "sv": "Mjölk"}
    )
    await session.commit()

    names = {}
    for language in ("en", "fi", "sv"):
        response = await client.post(SEARCH_URL, json={"language": language})
        names[language] = response.json()["items"][0]["name"]

    assert names == {"en": "Milk", "fi": "Maito", "sv": "Mjölk"}


async def test_missing_translation_falls_back_to_finnish(reference_data, session, client):
    await make_product(session, names={"en": "Milk", "fi": "Maito"})
    await session.commit()

    response = await client.post(SEARCH_URL, json={"language": "sv"})

    assert response.json()["items"][0]["name"] == "Maito"


@pytest.mark.parametrize("query", ["milk", "maito", "mjölk"], ids=["en", "fi", "sv"])
async def test_query_finds_a_product_by_its_name_in_each_language(
    reference_data, session, client, query
):
    await make_product(
        session,
        code="100001",
        names={"en": "Lactose free milk", "fi": "Laktoositon maito", "sv": "Laktosfri mjölk"},
    )
    await make_product(session, code="100002", names={"en": "Butter", "fi": "Voi", "sv": "Smör"})
    await session.commit()

    response = await client.post(SEARCH_URL, json={"query": query})

    body = response.json()
    assert body["total"] == 1
    assert [item["code"] for item in body["items"]] == ["100001"]


async def test_misspelled_query_still_finds_the_product(reference_data, session, client):
    await make_product(session, code="100001", names={"en": "Lactose free milk"})
    await make_product(session, code="100002", names={"en": "Butter"})
    await session.commit()

    response = await client.post(SEARCH_URL, json={"query": "lactose fre mlik"})

    assert [item["code"] for item in response.json()["items"]] == ["100001"]


async def test_query_results_are_ordered_by_relevance(reference_data, session, client):
    await make_product(
        session,
        code="100001",
        names={"en": "Cocoa drink"},
        marketing_texts={"en": "Tastes best with cold milk"},
        delivery_reliability=Decimal("0.99"),
    )
    await make_product(
        session, code="100002", names={"en": "Whole milk"}, delivery_reliability=Decimal("0.10")
    )
    await session.commit()

    response = await client.post(SEARCH_URL, json={"query": "milk"})

    items = response.json()["items"]
    assert [item["code"] for item in items] == ["100002", "100001"]
    assert items[0]["relevance"] > items[1]["relevance"]


async def test_browse_hits_have_no_relevance(reference_data, session, client):
    await make_product(session)
    await session.commit()

    response = await client.post(SEARCH_URL, json={})

    assert response.json()["items"][0]["relevance"] is None


async def test_hit_carries_the_product_attributes(reference_data, session, client):
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
        variable_unit=False,
        country_of_origin="fi",
        delivery_reliability=Decimal("0.975"),
        carbon_footprint=Decimal("1.250"),
    )
    await session.commit()

    response = await client.post(SEARCH_URL, json={})

    [hit] = response.json()["items"]
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
        "countryOfOrigin": "fi",
        "deliveryReliability": 0.975,
        "carbonFootprint": {"value": 1.25, "basis": "PRODUCT_GROUP_AVERAGE"},
    }
    assert {key: hit.get(key) for key in expected} == expected


async def test_hit_carries_units_deposit_flag_claims_diets_and_labels(
    reference_data, session, client
):
    await make_product(
        session,
        base_unit="ST",
        units={"ST": Decimal("1"), "KI": Decimal("12")},
        deposits=["PANT1"],
        claims=[("FREE_FROM", "LACTOSE")],
        diets=["VEGAN"],
        labels=["EU_ORGANIC_FARMING"],
    )
    await session.commit()

    response = await client.post(SEARCH_URL, json={})

    [hit] = response.json()["items"]
    assert sorted(hit["units"], key=lambda unit: unit["sizeInBaseUnits"]) == [
        {"code": "ST", "sizeInBaseUnits": 1.0},
        {"code": "KI", "sizeInBaseUnits": 12.0},
    ]
    assert hit["hasDeposit"] is True
    assert hit["claims"] == [{"type": "FREE_FROM", "element": "LACTOSE"}]
    assert hit["diets"] == ["VEGAN"]
    assert hit["labels"] == ["EU_ORGANIC_FARMING"]


async def test_product_without_deposits_has_no_deposit(reference_data, session, client):
    await make_product(session)
    await session.commit()

    response = await client.post(SEARCH_URL, json={})

    assert response.json()["items"][0]["hasDeposit"] is False


async def test_missing_reliability_carbon_footprint_and_brand_are_null(
    reference_data, session, client
):
    await make_product(session, brand=None, delivery_reliability=None, carbon_footprint=None)
    await session.commit()

    response = await client.post(SEARCH_URL, json={})

    [hit] = response.json()["items"]
    assert hit["deliveryReliability"] is None
    assert hit["carbonFootprint"] is None
    assert hit["brand"] is None


async def test_empty_body_is_a_valid_browse_request(client):
    response = await client.post(SEARCH_URL, json={})

    assert response.status_code == 200


async def test_limit_of_100_is_accepted(client):
    response = await client.post(SEARCH_URL, json={"limit": 100})

    assert response.status_code == 200


async def test_limit_above_100_is_rejected(client):
    response = await client.post(SEARCH_URL, json={"limit": 101})

    assert response.status_code == 422


async def test_search_request_is_documented_in_openapi(client):
    schema = (await client.get("/openapi.json")).json()

    request_body = schema["paths"][SEARCH_URL]["post"]["requestBody"]
    request_ref = request_body["content"]["application/json"]["schema"]["$ref"]
    request_model = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]

    assert request_model["properties"]["limit"]["maximum"] == 100
    assert set(request_model["properties"]) == {"query", "language", "limit", "offset"}


async def test_search_response_is_documented_in_openapi(client):
    schema = (await client.get("/openapi.json")).json()

    ok = schema["paths"][SEARCH_URL]["post"]["responses"]["200"]
    response_ref = ok["content"]["application/json"]["schema"]["$ref"]
    response_model = schema["components"]["schemas"][response_ref.rsplit("/", 1)[-1]]

    assert set(response_model["properties"]) == {"total", "items", "provenance"}
    assert set(schema["components"]["schemas"]["ProductHit"]["properties"]) == {
        "code",
        "name",
        "gtin",
        "categoryCode",
        "vendor",
        "brand",
        "salesUnit",
        "baseUnit",
        "allowedLotSize",
        "units",
        "variableUnit",
        "hasDeposit",
        "claims",
        "diets",
        "labels",
        "countryOfOrigin",
        "deliveryReliability",
        "carbonFootprint",
        "relevance",
    }
