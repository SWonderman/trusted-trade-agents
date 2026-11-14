"""
POST /api/v1/products/search, exercised over HTTP.
"""

from decimal import Decimal

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
