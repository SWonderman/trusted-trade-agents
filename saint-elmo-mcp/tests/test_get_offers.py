import json

import pytest
from conftest import text, tool_named

DELIVER_BY = "2030-06-03"

PROVENANCE = {
    "source": "Valio Aimo API",
    "fetchedAt": "2026-11-14T10:00:00Z",
    "validUntil": "2030-06-01T12:00:00Z",
    "cached": False,
}

# As the backend answers the milk example (#12): 1000 L of 463038 is 50 KI
MILK_OFFER = {
    "productCode": "463038",
    "name": "Valio Eila semi skimmed milk drink 10 l novobox lactose free",
    "salesUnit": "KI",
    "price": {
        "perSalesUnit": {"net": 31.31, "gross": 35.69},
        "taxRate": 14.0,
        "currency": "EUR",
        "comparisonPrice": {"value": 1.57, "unit": "L"},
        "customerSpecific": False,
        "validFrom": "2026-11-01T00:00:00Z",
        "validTo": None,
    },
    "availability": {
        "logisticModel": "STOCK",
        "availableAmount": 400.0,
        "availableAmountKnown": True,
        "earliestDate": "2030-06-02",
        "closingTime": "2030-06-01T12:00:00Z",
        "salesBlocked": False,
        "meetsDeadline": True,
    },
    "quantity": {
        "requested": {"value": 1000.0, "unit": "L"},
        "conversion": {
            "perSalesUnit": {"value": 20.0, "unit": "L"},
            "basis": "PRICE_COMPARISON",
            "crossCheck": "AGREES",
        },
        "salesUnits": 50.0,
        "lotSize": 1.0,
        "roundedUp": False,
        "delivered": {"value": 1000.0, "unit": "L"},
        "lineTotal": {"net": 1565.5, "gross": 1784.5},
        "coveredByAvailability": True,
    },
    "deliveryReliability": 0.982,
    "carbonFootprint": {"value": 1.1, "basis": "PRODUCT_GROUP_AVERAGE"},
    "reasonCodes": [],
    "provenance": PROVENANCE,
}

# A supplier-shipped product: the amount is unknown, not zero (#12)
TERMINAL_OFFER = {
    **MILK_OFFER,
    "productCode": "123456",
    "availability": {
        **MILK_OFFER["availability"],
        "logisticModel": "TERMINAL",
        "availableAmount": None,
        "availableAmountKnown": False,
    },
    "quantity": {
        **MILK_OFFER["quantity"],
        "requested": {"value": 10.0, "unit": "KI"},
        "conversion": None,
        "salesUnits": 10.0,
        "delivered": {"value": 10.0, "unit": "KI"},
        "lineTotal": {"net": 313.1, "gross": 356.9},
        "coveredByAvailability": None,
    },
}

# No price, not deliverable, no quantity asked for
BARE_OFFER = {
    "productCode": "999001",
    "name": None,
    "salesUnit": "ST",
    "price": None,
    "availability": None,
    "quantity": None,
    "deliveryReliability": None,
    "carbonFootprint": None,
    "reasonCodes": ["NO_PRICE", "NOT_DELIVERABLE"],
    "provenance": {**PROVENANCE, "validUntil": None, "cached": True},
}


def offers_response(*items: dict) -> dict:
    return {"deliverBy": DELIVER_BY, "evaluatedAt": "2026-11-14T10:00:01Z", "items": list(items)}


def error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message, "requestId": "r-1"}}


async def test_get_offers_is_listed_with_input_and_output_schemas(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        tool = await tool_named(client, "get_offers")

    assert set(tool.input_schema["required"]) == {"deliverBy", "items"}
    assert tool.output_schema is not None
    assert {"deliverBy", "evaluatedAt", "items"} <= set(tool.output_schema["properties"])
    assert tool.annotations is not None and tool.description is not None
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.open_world_hint is False
    for phrase in ("binding on nothing", "CLOSING_TIME_PASSED", "create_quote", "crossCheck"):
        assert phrase in tool.description, phrase


async def test_milk_example_sends_only_given_fields_and_returns_the_conversion(connect, backend):
    backend.respond_json(200, offers_response(MILK_OFFER))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "get_offers",
            {
                "deliverBy": DELIVER_BY,
                "items": [{"productCode": "463038", "quantity": 1000, "unit": "L"}],
            },
        )

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "POST"
    assert request.url.path == "/api/v1/offers"
    assert request.headers["authorization"] == "Bearer k1"
    assert json.loads(request.content) == {
        "deliverBy": DELIVER_BY,
        "items": [{"productCode": "463038", "quantity": 1000, "unit": "L"}],
    }

    item = result.structured_content["items"][0]
    assert item["quantity"]["conversion"] == {
        "perSalesUnit": {"value": 20.0, "unit": "L"},
        "basis": "PRICE_COMPARISON",
        "crossCheck": "AGREES",
    }
    assert item["quantity"]["salesUnits"] == 50.0
    assert item["quantity"]["lineTotal"] == {"net": 1565.5, "gross": 1784.5}
    assert item["price"]["perSalesUnit"] == {"net": 31.31, "gross": 35.69}
    assert item["availability"]["meetsDeadline"] is True
    assert item["provenance"] == PROVENANCE
    assert result.structured_content["deliverBy"] == DELIVER_BY


async def test_an_item_without_quantity_is_sent_as_just_its_code(connect, backend):
    backend.respond_json(200, offers_response(BARE_OFFER))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "get_offers",
            {"deliverBy": DELIVER_BY, "items": [{"productCode": "999001"}], "language": "fi"},
        )

    assert not result.is_error, text(result)
    assert json.loads(backend.requests[0].content) == {
        "deliverBy": DELIVER_BY,
        "items": [{"productCode": "999001"}],
        "language": "fi",
    }
    item = result.structured_content["items"][0]
    assert item["price"] is None
    assert item["availability"] is None
    assert item["quantity"] is None
    assert item["reasonCodes"] == ["NO_PRICE", "NOT_DELIVERABLE"]


async def test_terminal_item_with_unknown_amount_validates(connect, backend):
    backend.respond_json(200, offers_response(TERMINAL_OFFER))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "get_offers",
            {"deliverBy": DELIVER_BY, "items": [{"productCode": "123456", "quantity": 10}]},
        )

    assert not result.is_error, text(result)
    item = result.structured_content["items"][0]
    assert item["availability"]["logisticModel"] == "TERMINAL"
    assert item["availability"]["availableAmount"] is None
    assert item["quantity"]["coveredByAvailability"] is None
    assert item["quantity"]["conversion"] is None


@pytest.mark.parametrize("count", [0, 51])
async def test_item_count_outside_1_to_50_is_rejected_without_a_backend_call(
    connect, backend, count
):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "get_offers",
            {"deliverBy": DELIVER_BY, "items": [{"productCode": f"{i}"} for i in range(count)]},
        )

    assert result.is_error
    assert backend.requests == []


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (404, "PRODUCT_NOT_FOUND", "Unknown product codes: 999990, 999991"),
        (409, "CUSTOMER_NUMBER_MISSING", "The buyer organisation has no Valio Aimo customer number"),
        (503, "VALIO_AIMO_UNAVAILABLE", "The Valio Aimo price and availability API is unavailable"),
    ],
)
async def test_backend_errors_come_back_as_errors_with_their_codes(
    connect, backend, status, code, message
):
    backend.respond_json(status, error(code, message))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "get_offers", {"deliverBy": DELIVER_BY, "items": [{"productCode": "999990"}]}
        )

    assert result.is_error
    assert f"{code}: {message}" in text(result)


async def test_missing_key_is_an_error_and_backend_is_not_called(connect, backend):
    async with connect() as client:
        result = await client.call_tool(
            "get_offers", {"deliverBy": DELIVER_BY, "items": [{"productCode": "463038"}]}
        )

    assert result.is_error
    assert "MISSING_AGENT_KEY" in text(result)
    assert backend.requests == []


async def test_an_impossible_deliver_by_date_is_rejected_without_a_backend_call(connect, backend):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "get_offers", {"deliverBy": "2026-13-45", "items": [{"productCode": "463038"}]}
        )

    assert result.is_error
    assert backend.requests == []
