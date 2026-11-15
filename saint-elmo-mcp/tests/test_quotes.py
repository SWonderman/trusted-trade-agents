import json

import pytest
from conftest import assert_sends_shortfalls_to_find_substitutes, error, text, tool_named
from test_get_offers import DELIVER_BY, MILK_OFFER

QUOTE_ID = "3f2b8c1e-5d4a-4b6e-9a7c-1e2d3f4a5b6c"
BUYER_REQUEST = "1,000 litres of lactose-free milk by Monday"
RATIONALE = "Valio Eila 10 l is lactose free and meets the deadline."

# As the backend answers the milk example for dairy-restock (#14): 1000 L of 463038
# is 50 KI, 1784.50 EUR gross, over autoApproveUpTo 1500 so a human decides
MILK_QUOTE = {
    "quoteId": QUOTE_ID,
    "status": "QUOTED",
    "createdAt": "2026-11-14T10:00:02Z",
    "expiresAt": "2026-11-14T10:30:02Z",
    "deliverBy": DELIVER_BY,
    "lines": [
        {
            **MILK_OFFER,
            "position": 1,
            "substitutesFor": None,
            "outcome": "NEEDS_HUMAN",
            "reasons": [],
        }
    ],
    "totals": {"net": 1565.5, "gross": 1784.5, "currency": "EUR"},
    "deposits": [],
    "policy": {
        "outcome": "NEEDS_HUMAN",
        "reasons": [
            {
                "code": "OVER_AUTO_APPROVE_LIMIT",
                "severity": "NEEDS_HUMAN",
                "lineRef": None,
                "message": "The quote total 1784.50 EUR is over the auto-approve limit of "
                "1500.00 EUR.",
                "facts": {"total": 1784.5, "autoApproveUpTo": 1500.0},
            }
        ],
        "mandateVersion": 1,
    },
    "buyerRequest": BUYER_REQUEST,
    "rationale": RATIONALE,
    "previousQuoteId": None,
}

MILK_LINE = {"productCode": "463038", "quantity": 1000, "unit": "L"}


def create_args(**overrides) -> dict:
    return {
        "deliverBy": DELIVER_BY,
        "lines": [MILK_LINE],
        "buyerRequest": BUYER_REQUEST,
        "rationale": RATIONALE,
        **overrides,
    }


async def test_milk_example_sends_only_given_fields_and_returns_the_policy_outcome(
    connect, backend
):
    backend.respond_json(201, MILK_QUOTE)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("create_quote", create_args())

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "POST"
    assert request.url.path == "/api/v1/quotes"
    assert request.headers["authorization"] == "Bearer k1"
    assert json.loads(request.content) == {
        "deliverBy": DELIVER_BY,
        "lines": [MILK_LINE],
        "buyerRequest": BUYER_REQUEST,
        "rationale": RATIONALE,
    }
    assert result.structured_content == MILK_QUOTE
    line = result.structured_content["lines"][0]
    assert line["quantity"]["salesUnits"] == 50.0
    assert line["salesUnit"] == "KI"
    assert result.structured_content["totals"]["gross"] == 1784.5
    assert result.structured_content["policy"]["outcome"] == "NEEDS_HUMAN"


# Every top-level field of the backend's QuoteResponse (#14)
QUOTE_FIELDS = set(MILK_QUOTE)

# A milk line the buyer's mandate rejects (#13): blocked vendor, closing time passed
REJECTED_QUOTE = {
    **MILK_QUOTE,
    "lines": [
        {
            **MILK_QUOTE["lines"][0],
            "reasonCodes": ["CLOSING_TIME_PASSED"],
            "outcome": "REJECT",
            "reasons": [
                {
                    "code": "CLOSING_TIME_PASSED",
                    "severity": "REJECT",
                    "lineRef": "1",
                    "message": "The order cut-off for 2030-06-03 has passed.",
                    "facts": {"closingTime": "2030-06-01T12:00:00Z"},
                },
                {
                    "code": "BLOCKED_VENDOR",
                    "severity": "REJECT",
                    "lineRef": "1",
                    "message": "Valio is a blocked vendor.",
                    "facts": {"vendor": "Valio"},
                },
            ],
        }
    ],
    "policy": {
        **MILK_QUOTE["policy"],
        "outcome": "REJECT",
        "reasons": [
            {
                "code": "CLOSING_TIME_PASSED",
                "severity": "REJECT",
                "lineRef": "1",
                "message": "The order cut-off for 2030-06-03 has passed.",
                "facts": {"closingTime": "2030-06-01T12:00:00Z"},
            },
            {
                "code": "BLOCKED_VENDOR",
                "severity": "REJECT",
                "lineRef": "1",
                "message": "Valio is a blocked vendor.",
                "facts": {"vendor": "Valio"},
            },
        ],
    },
}

EXPIRED_QUOTE = {
    **MILK_QUOTE,
    "status": "EXPIRED",
    "deposits": [{"materialCode": "200001", "quantity": 50.0, "unit": "ST"}],
}


async def test_both_tools_are_listed_with_input_and_output_schemas(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        create = await tool_named(client, "create_quote")
        get = await tool_named(client, "get_quote")

    assert set(create.input_schema["required"]) == {
        "deliverBy",
        "lines",
        "buyerRequest",
        "rationale",
    }
    assert "previousQuoteId" in create.input_schema["properties"]
    assert set(get.input_schema["required"]) == {"quoteId"}
    for tool in (create, get):
        assert tool.output_schema is not None
        assert set(tool.output_schema["properties"]) == QUOTE_FIELDS

    assert create.annotations is not None and create.description is not None
    assert create.annotations.read_only_hint is False
    assert create.annotations.destructive_hint is False
    assert create.annotations.idempotent_hint is False
    assert create.annotations.open_world_hint is False
    for phrase in (
        "buyerRequest",
        "rationale",
        "approvers",
        "audit trail",
        "L or KG",
        "substitutesFor",
        "not an error",
        "policy.reasons",
        "previousQuoteId",
        "expiresAt",
        "place_order",
    ):
        assert phrase in create.description, phrase

    assert get.annotations is not None and get.description is not None
    assert get.annotations.read_only_hint is True
    assert get.annotations.idempotent_hint is True
    assert 'status: "EXPIRED"' in get.description


async def test_a_rejected_quote_is_a_normal_result_with_its_reasons(connect, backend):
    backend.respond_json(201, REJECTED_QUOTE)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("create_quote", create_args())

    assert not result.is_error, text(result)
    policy = result.structured_content["policy"]
    assert policy["outcome"] == "REJECT"
    assert [r["code"] for r in policy["reasons"]] == ["CLOSING_TIME_PASSED", "BLOCKED_VENDOR"]
    assert result.structured_content["lines"][0]["outcome"] == "REJECT"


async def test_a_revision_sends_its_substitute_and_previous_quote(connect, backend):
    previous = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"
    substitute = {
        "productCode": "463040",
        "quantity": 1000,
        "unit": "L",
        "substitutesFor": "463038",
    }
    backend.respond_json(201, {**MILK_QUOTE, "previousQuoteId": previous})

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "create_quote", create_args(lines=[substitute], previousQuoteId=previous)
        )

    assert not result.is_error, text(result)
    body = json.loads(backend.requests[0].content)
    assert body["lines"] == [substitute]
    assert body["previousQuoteId"] == previous
    assert result.structured_content["previousQuoteId"] == previous


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"buyerRequest": None}, id="missing buyerRequest"),
        pytest.param({"rationale": None}, id="missing rationale"),
        pytest.param({"buyerRequest": "x" * 2001}, id="buyerRequest over 2000"),
        pytest.param({"rationale": "x" * 2001}, id="rationale over 2000"),
        pytest.param({"buyerRequest": ""}, id="empty buyerRequest"),
        pytest.param({"lines": []}, id="no lines"),
        pytest.param({"lines": [MILK_LINE] * 51}, id="51 lines"),
        pytest.param({"lines": [{"productCode": "463038"}]}, id="line without quantity"),
        pytest.param({"previousQuoteId": "not-a-uuid"}, id="malformed previousQuoteId"),
        pytest.param(
            {"lines": [{**MILK_LINE, "substitutesFor": "463038"}]},
            id="line substitutes for its own product",
        ),
    ],
)
async def test_out_of_bounds_input_is_rejected_without_a_backend_call(connect, backend, overrides):
    args = {k: v for k, v in create_args(**overrides).items() if v is not None}

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("create_quote", args)

    assert result.is_error
    assert backend.requests == []


async def test_text_of_exactly_2000_characters_is_accepted(connect, backend):
    backend.respond_json(201, MILK_QUOTE)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "create_quote", create_args(buyerRequest="x" * 2000, rationale="y" * 2000)
        )

    assert not result.is_error, text(result)


async def test_get_quote_reads_an_expired_quote_by_its_id(connect, backend):
    backend.respond_json(200, EXPIRED_QUOTE)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_quote", {"quoteId": QUOTE_ID})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "GET"
    assert request.url.raw_path == f"/api/v1/quotes/{QUOTE_ID}".encode()
    assert request.headers["authorization"] == "Bearer k1"
    assert result.structured_content == EXPIRED_QUOTE


@pytest.mark.parametrize("quote_id", ["a/b c", "", QUOTE_ID[:-1]])
async def test_get_quote_with_a_malformed_id_is_rejected_without_a_backend_call(
    connect, backend, quote_id
):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_quote", {"quoteId": quote_id})

    assert result.is_error
    assert backend.requests == []


async def test_get_quote_for_an_unknown_id_is_an_error(connect, backend):
    backend.respond_json(
        404, error("QUOTE_NOT_FOUND", "No quote with this id in your buyer organisation")
    )

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_quote", {"quoteId": QUOTE_ID})

    assert result.is_error
    assert "QUOTE_NOT_FOUND: No quote with this id in your buyer organisation" in text(result)


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (404, "PRODUCT_NOT_FOUND", "Unknown product codes: 999990, 999991"),
        (404, "QUOTE_NOT_FOUND", "No previous quote with this id in your buyer organisation"),
        (
            409,
            "CUSTOMER_NUMBER_MISSING",
            "The buyer organisation has no Valio Aimo customer number",
        ),
        (503, "VALIO_AIMO_UNAVAILABLE", "The Valio Aimo price and availability API is unavailable"),
    ],
)
async def test_create_quote_backend_errors_come_back_as_errors_with_their_codes(
    connect, backend, status, code, message
):
    backend.respond_json(status, error(code, message))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("create_quote", create_args())

    assert result.is_error
    assert f"{code}: {message}" in text(result)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("policy", "outcome"), "MAYBE"),
        (("status",), "DRAFT"),
    ],
)
async def test_an_outcome_or_status_the_tool_does_not_know_fails_loudly(
    connect, backend, path, value
):
    quote = json.loads(json.dumps(MILK_QUOTE))
    target = quote
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    backend.respond_json(201, quote)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("create_quote", create_args())

    assert result.is_error
    assert "BACKEND_CONTRACT_MISMATCH" in text(result)


@pytest.mark.parametrize(
    ("tool", "args"),
    [("create_quote", create_args()), ("get_quote", {"quoteId": QUOTE_ID})],
)
async def test_missing_key_is_an_error_and_backend_is_not_called(connect, backend, tool, args):
    async with connect() as client:
        result = await client.call_tool(tool, args)

    assert result.is_error
    assert "MISSING_AGENT_KEY" in text(result)
    assert backend.requests == []


async def test_create_quote_sends_a_shortfall_on_a_line_to_find_substitutes(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        tool = await tool_named(client, "create_quote")

    assert_sends_shortfalls_to_find_substitutes(tool.description)
