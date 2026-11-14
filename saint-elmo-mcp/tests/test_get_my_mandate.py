import pytest
from conftest import text, tool_named

# As the backend answers for the seeded dairy-restock agent (#11, db/seeders/demo.py)
DAIRY_RESTOCK_MANDATE = {
    "id": "6f1c2b9e-0d4a-4a8e-9c1e-3b7f5d2a1e01",
    "version": 1,
    "agent": {"id": "0b8e4f1a-2c3d-4e5f-8a9b-1c2d3e4f5a6b", "name": "dairy-restock"},
    "buyerOrganisation": {"name": "Hotel chain"},
    "currency": "EUR",
    "maxOrderTotal": 2000.0,
    "periodSpendCap": 5000.0,
    "spendPeriod": "WEEK",
    "categorySpendCaps": [],
    "allowedCategoryCodes": ["10400", "10401"],
    "blockedCategoryCodes": [],
    "allowedVendors": [],
    "blockedVendors": [],
    "allowedCountriesOfOrigin": [],
    "requiredClaims": [{"type": "FREE_FROM", "element": "LACTOSE"}],
    "requiredLabels": [],
    "requiredDiets": [],
    "excludedAllergens": [],
    "allergenStrictness": "contains",
    "substitutionPolicy": "IF_REQUIREMENTS_HOLD",
    "maxSubstitutePriceIncreasePct": 10.0,
    "laterDeliveryNeedsApproval": True,
    "minDeliveryReliability": None,
    "autoApproveUpTo": 1500.0,
    "periodSpend": {
        "periodStart": "2026-11-09T00:00:00+02:00",
        "periodEnd": "2026-11-16T00:00:00+02:00",
        "committed": 0.0,
        "remaining": 5000.0,
    },
}

# Every top-level field of the backend's MandateResponse (#11)
MANDATE_FIELDS = set(DAIRY_RESTOCK_MANDATE)


def error(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message, "requestId": "r-1"}}


async def test_get_my_mandate_is_listed_with_no_inputs_and_every_output_field(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        tool = await tool_named(client, "get_my_mandate")

    assert tool.input_schema.get("properties", {}) == {}
    assert tool.output_schema is not None
    assert set(tool.output_schema["properties"]) == MANDATE_FIELDS
    assert tool.annotations is not None and tool.description is not None
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.open_world_hint is False
    for phrase in (
        "first",
        "search_products",
        "requiredClaims",
        "empty allow-list",
        "autoApproveUpTo",
        "maxOrderTotal",
        "periodSpend.remaining",
        "never change",
        "MANDATE_NOT_FOUND",
        "PERMISSION_DENIED",
    ):
        assert phrase in tool.description, phrase


async def test_dairy_restock_mandate_is_read_with_the_agent_key_and_no_ids(connect, backend):
    backend.respond_json(200, DAIRY_RESTOCK_MANDATE)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_my_mandate", {})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "GET"
    assert request.url.path == "/api/v1/agents/me/mandate"
    assert request.url.query == b""
    assert request.content == b""
    assert request.headers["authorization"] == "Bearer k1"
    assert result.structured_content == DAIRY_RESTOCK_MANDATE


async def test_set_optional_limits_and_caps_validate(connect, backend):
    mandate = {
        **DAIRY_RESTOCK_MANDATE,
        "spendPeriod": "MONTH",
        "categorySpendCaps": [{"categoryCode": "10400", "cap": 800.0}],
        "blockedVendors": ["Acme"],
        "excludedAllergens": ["AM", "AW"],
        "allergenStrictness": "declared_free",
        "substitutionPolicy": "ALWAYS_NEEDS_APPROVAL",
        "minDeliveryReliability": 0.95,
    }
    backend.respond_json(200, mandate)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_my_mandate", {})

    assert not result.is_error, text(result)
    assert result.structured_content == mandate


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spendPeriod", "DAY"),
        ("substitutionPolicy", "SOMETIMES"),
        ("allergenStrictness", "lenient"),
    ],
)
async def test_an_enum_value_the_tool_does_not_know_fails_loudly(connect, backend, field, value):
    backend.respond_json(200, {**DAIRY_RESTOCK_MANDATE, field: value})

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_my_mandate", {})

    assert result.is_error
    assert "BACKEND_CONTRACT_MISMATCH" in text(result)
    assert field in text(result)


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (404, "MANDATE_NOT_FOUND", "The agent has no mandate"),
        (403, "PERMISSION_DENIED", "The token lacks the mandate:read scope"),
    ],
)
async def test_backend_errors_come_back_as_errors_with_their_codes(
    connect, backend, status, code, message
):
    backend.respond_json(status, error(code, message))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_my_mandate", {})

    assert result.is_error
    assert f"{code}: {message}" in text(result)


async def test_missing_key_is_an_error_and_backend_is_not_called(connect, backend):
    async with connect() as client:
        result = await client.call_tool("get_my_mandate", {})

    assert result.is_error
    assert "MISSING_AGENT_KEY" in text(result)
    assert backend.requests == []
