"""
POST /api/v1/products/search, exercised over HTTP.
"""

SEARCH_URL = "/api/v1/products/search"


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
