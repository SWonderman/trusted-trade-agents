import json

import httpx
import pytest

from conftest import MILK_HIT, search_response


FILTERS = {
    "categoryCodes",
    "vendors",
    "requiredClaims",
    "requiredDiets",
    "requiredLabels",
    "countriesOfOrigin",
    "minDeliveryReliability",
}


def text(result) -> str:
    return "\n".join(block.text for block in result.content if block.type == "text")


async def test_lists_only_search_products_with_rest_field_names(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        tools = (await client.list_tools()).tools

    assert [t.name for t in tools] == ["search_products"]
    tool = tools[0]
    assert set(tool.input_schema["properties"]) == {"query", "language", "limit", "offset"} | FILTERS
    assert tool.output_schema is not None
    assert {"total", "items", "provenance"} <= set(tool.output_schema["properties"])
    assert tool.annotations.read_only_hint is True


async def test_required_claims_items_are_typed_type_and_element(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        (tool,) = (await client.list_tools()).tools

    schema = tool.input_schema
    items = schema["properties"]["requiredClaims"]["anyOf"][0]["items"]
    if "$ref" in items:
        items = schema["$defs"][items["$ref"].rsplit("/", 1)[-1]]
    assert set(items["properties"]) == {"type", "element"}
    assert set(items["required"]) == {"type", "element"}
    assert "get_vocabulary" in schema["properties"]["requiredClaims"]["description"]
    assert "UNKNOWN_CODE" in tool.description


async def test_server_sends_workflow_instructions(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        instructions = client.instructions

    assert instructions is not None
    for step in ("get_my_mandate", "search_products", "get_offers", "create_quote", "place_order"):
        assert step in instructions
    assert "Unknown is not" in instructions


@pytest.mark.parametrize(
    "headers",
    [{"X-Agent-Key": "k1"}, {"Authorization": "Bearer k1"}],
    ids=["x-agent-key", "bearer"],
)
async def test_forwards_agent_key_as_bearer(connect, backend, headers):
    backend.respond_json(200, search_response(MILK_HIT))

    async with connect(headers) as client:
        result = await client.call_tool("search_products", {"query": "lactose free milk"})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "POST"
    assert request.url.path == "/api/v1/products/search"
    assert request.headers["authorization"] == "Bearer k1"
    assert json.loads(request.content) == {
        "query": "lactose free milk",
        "language": "en",
        "limit": 10,
        "offset": 0,
    }


async def test_filters_are_forwarded_unchanged(connect, backend):
    backend.respond_json(200, search_response(MILK_HIT))
    filters = {
        "categoryCodes": ["101010", "101020"],
        "vendors": ["Valio"],
        "requiredClaims": [{"type": "FREE_FROM", "element": "LACTOSE"}],
        "requiredDiets": ["VEGAN"],
        "requiredLabels": ["EU_ORGANIC_FARMING"],
        "countriesOfOrigin": ["FI", "se"],
        "minDeliveryReliability": 0.95,
    }

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("search_products", {"query": "milk", **filters})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert json.loads(request.content) == {
        "query": "milk",
        "language": "en",
        "limit": 10,
        "offset": 0,
        **filters,
    }


async def test_only_given_filters_are_sent(connect, backend):
    backend.respond_json(200, search_response())

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("search_products", {"requiredDiets": ["VEGAN"]})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert json.loads(request.content) == {
        "language": "en",
        "limit": 10,
        "offset": 0,
        "requiredDiets": ["VEGAN"],
    }


async def test_missing_key_is_an_error_and_backend_is_not_called(connect, backend):
    async with connect() as client:
        result = await client.call_tool("search_products", {"query": "milk"})

    assert result.is_error
    assert "MISSING_AGENT_KEY" in text(result)
    assert "X-Agent-Key" in text(result)
    assert backend.requests == []


async def test_backend_error_envelope_reaches_the_agent(connect, backend):
    backend.respond_json(
        422,
        {
            "error": {
                "code": "UNKNOWN_CODE",
                "message": "Unknown codes: requiredLabels=[ORGANIC]",
                "requestId": "req-123",
                "details": [{"field": "requiredLabels", "message": "ORGANIC is not a label code"}],
            }
        },
    )

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("search_products", {"query": "milk"})

    assert result.is_error
    message = text(result)
    assert "UNKNOWN_CODE: Unknown codes: requiredLabels=[ORGANIC]" in message
    assert "requiredLabels: ORGANIC is not a label code" in message
    assert "req-123" in message


async def test_unreachable_backend_is_backend_unavailable(connect):
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with connect({"X-Agent-Key": "k1"}, backend_transport=httpx.MockTransport(refuse)) as client:
        result = await client.call_tool("search_products", {"query": "milk"})

    assert result.is_error
    assert "BACKEND_UNAVAILABLE" in text(result)


async def test_non_envelope_5xx_is_backend_unavailable(connect, backend):
    backend.handler = lambda _: httpx.Response(502, text="Bad Gateway")

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("search_products", {"query": "milk"})

    assert result.is_error
    assert "BACKEND_UNAVAILABLE" in text(result)


@pytest.mark.parametrize("limit", [0, 101])
async def test_limit_outside_1_to_100_is_rejected_without_backend_call(connect, backend, limit):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("search_products", {"limit": limit})

    assert result.is_error
    assert backend.requests == []


@pytest.mark.parametrize("value", [-0.1, 1.5])
async def test_min_delivery_reliability_outside_0_to_1_is_rejected_without_backend_call(
    connect, backend, value
):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("search_products", {"minDeliveryReliability": value})

    assert result.is_error
    assert "minDeliveryReliability" in text(result)
    assert backend.requests == []


async def test_unknown_filter_codes_come_back_listing_every_bad_code(connect, backend):
    # Envelope as the backend's UnknownFilterCodes builds it (#3)
    backend.respond_json(
        422,
        {
            "error": {
                "code": "UNKNOWN_CODE",
                "message": "Unknown codes: categoryCodes=[999999], "
                "requiredClaims=[FREE_FORM, LACTOS], requiredDiets=[CARNIVORE], "
                "requiredLabels=[ORGANIC]",
                "requestId": "req-456",
            }
        },
    )

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "search_products",
            {
                "categoryCodes": ["999999"],
                "requiredClaims": [{"type": "FREE_FORM", "element": "LACTOS"}],
                "requiredDiets": ["CARNIVORE"],
                "requiredLabels": ["ORGANIC"],
            },
        )

    assert result.is_error
    message = text(result)
    assert "UNKNOWN_CODE: Unknown codes:" in message
    for listed in (
        "categoryCodes=[999999]",
        "requiredClaims=[FREE_FORM, LACTOS]",
        "requiredDiets=[CARNIVORE]",
        "requiredLabels=[ORGANIC]",
    ):
        assert listed in message
    assert "req-456" in message


async def test_success_returns_structured_content_in_camel_case(connect, backend):
    backend.respond_json(200, search_response(MILK_HIT, total=42))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("search_products", {"query": "milk", "limit": 5})

    assert not result.is_error, text(result)
    data = result.structured_content
    assert data["total"] == 42
    hit = data["items"][0]
    assert hit["code"] == "463038"
    assert hit["salesUnit"] == "KI"
    assert hit["claims"] == [{"type": "FREE_FROM", "element": "LACTOSE"}]
    assert hit["deliveryReliability"] is None
    assert hit["carbonFootprint"]["basis"] == "PRODUCT_GROUP_AVERAGE"
    assert "somethingTheAgentDoesNotNeed" not in hit
    assert data["provenance"]["source"].startswith("Valio Aimo")


async def test_backend_shape_drift_is_reported_not_crashed(connect, backend):
    backend.respond_json(200, {"items": [], "provenance": {"source": "x"}})  # no total

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("search_products", {"query": "milk"})

    assert result.is_error
    assert "BACKEND_CONTRACT_MISMATCH" in text(result)
    assert "total" in text(result)
