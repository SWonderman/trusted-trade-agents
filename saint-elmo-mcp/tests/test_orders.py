import json

import pytest

from conftest import error, text, tool_named
from test_get_offers import DELIVER_BY
from test_quotes import BUYER_REQUEST, MILK_QUOTE, QUOTE_ID, RATIONALE

ORDER_ID = "7c1d2e3f-4a5b-4c6d-8e7f-9a0b1c2d3e4f"

# As the backend answers placing MILK_QUOTE under a mandate that auto-approves it (#15)
PLACED_ORDER = {
    "orderId": ORDER_ID,
    "quoteId": QUOTE_ID,
    "status": "PLACED",
    "createdAt": "2026-11-14T10:05:00Z",
    "agent": {"id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d", "name": "dairy-restock"},
    "deliverBy": DELIVER_BY,
    "lines": [{**MILK_QUOTE["lines"][0], "outcome": "AUTO_APPROVE"}],
    "totals": {"net": 1565.5, "gross": 1784.5, "currency": "EUR"},
    "deposits": [],
    "policy": {"outcome": "AUTO_APPROVE", "reasons": [], "mandateVersion": 2},
    "changes": [],
    "buyerRequest": BUYER_REQUEST,
    "rationale": RATIONALE,
    "statusHistory": [
        {"status": "CONFIRMED", "at": "2026-11-14T10:05:00Z", "by": "agent:dairy-restock"},
        {"status": "PLACED", "at": "2026-11-14T10:05:00Z", "by": "system"},
    ],
    "approverNote": None,
    "decidedAt": None,
    "checkAgainAfterSeconds": None,
}


async def test_place_order_commits_the_quote_and_returns_the_placed_order(connect, backend):
    backend.respond_json(201, PLACED_ORDER)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("place_order", {"quoteId": QUOTE_ID})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "POST"
    assert request.url.path == "/api/v1/orders"
    assert request.headers["authorization"] == "Bearer k1"
    assert json.loads(request.content) == {"quoteId": QUOTE_ID}
    assert result.structured_content == PLACED_ORDER


# The price rose between quote and order, pushing the total over autoApproveUpTo
PENDING_ORDER = {
    **PLACED_ORDER,
    "status": "PENDING_APPROVAL",
    "lines": MILK_QUOTE["lines"],
    "totals": {"net": 1615.5, "gross": 1841.5, "currency": "EUR"},
    "policy": {**MILK_QUOTE["policy"], "mandateVersion": 2},
    "changes": [{"lineRef": "1", "field": "unitPrice", "quoted": 31.31, "now": 32.31}],
    "statusHistory": [
        {"status": "PENDING_APPROVAL", "at": "2026-11-14T10:05:00Z", "by": "agent:dairy-restock"}
    ],
    "checkAgainAfterSeconds": 30,
}

# A human rejected the pending order, with a note
DECIDED_ORDER = {
    **PENDING_ORDER,
    "status": "REJECTED",
    "statusHistory": [
        *PENDING_ORDER["statusHistory"],
        {"status": "REJECTED", "at": "2026-11-14T11:00:00Z", "by": "user:Aino Virtanen"},
    ],
    "approverNote": "Too much milk for this week; order 500 L instead.",
    "decidedAt": "2026-11-14T11:00:00Z",
    "checkAgainAfterSeconds": None,
}

# The live re-check rejected the order outright: still a 201 with reasons
REJECTED_ORDER = {
    **PLACED_ORDER,
    "status": "REJECTED",
    "policy": {
        "outcome": "REJECT",
        "reasons": [
            {
                "code": "SALES_BLOCKED",
                "severity": "REJECT",
                "lineRef": "1",
                "message": "463038 is blocked from sale.",
                "facts": {},
            }
        ],
        "mandateVersion": 2,
    },
    "changes": [{"lineRef": "1", "field": "salesBlocked", "quoted": False, "now": True}],
    "statusHistory": [
        {"status": "REJECTED", "at": "2026-11-14T10:05:00Z", "by": "agent:dairy-restock"}
    ],
}


@pytest.mark.parametrize(
    "order", [PENDING_ORDER, REJECTED_ORDER], ids=["pending approval", "rejected"]
)
async def test_pending_or_rejected_orders_are_normal_results(connect, backend, order):
    backend.respond_json(201, order)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("place_order", {"quoteId": QUOTE_ID})

    assert not result.is_error, text(result)
    assert result.structured_content == order


async def test_an_already_ordered_quote_is_an_error_naming_the_existing_order(connect, backend):
    backend.respond_json(
        409,
        {
            "error": {
                "code": "QUOTE_ALREADY_ORDERED",
                "message": "An order was already placed from this quote; `details.orderId` "
                "is that order",
                "requestId": "r-1",
                "details": {"orderId": ORDER_ID},
            }
        },
    )

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("place_order", {"quoteId": QUOTE_ID})

    assert result.is_error
    assert "QUOTE_ALREADY_ORDERED: An order was already placed" in text(result)
    assert f"orderId: {ORDER_ID}" in text(result)


async def test_get_order_status_reads_a_decided_order_with_its_history_and_note(
    connect, backend
):
    backend.respond_json(200, DECIDED_ORDER)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_order_status", {"orderId": ORDER_ID})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "GET"
    assert request.url.raw_path == f"/api/v1/orders/{ORDER_ID}".encode()
    assert request.headers["authorization"] == "Bearer k1"
    assert result.structured_content == DECIDED_ORDER


@pytest.mark.parametrize("order_id", ["a/b c", "", ORDER_ID[:-1]])
async def test_get_order_status_with_a_malformed_id_is_rejected_without_a_backend_call(
    connect, backend, order_id
):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_order_status", {"orderId": order_id})

    assert result.is_error
    assert backend.requests == []


async def test_list_orders_sends_the_filter_and_page_and_returns_most_recent_first(
    connect, backend
):
    listing = {"total": 3, "items": [PENDING_ORDER]}
    backend.respond_json(200, listing)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "list_orders", {"status": "PENDING_APPROVAL", "limit": 1, "offset": 2}
        )

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "GET"
    assert request.url.path == "/api/v1/orders"
    assert dict(request.url.params) == {"status": "PENDING_APPROVAL", "limit": "1", "offset": "2"}
    assert result.structured_content == listing


async def test_list_orders_without_arguments_leaves_the_defaults_to_the_backend(
    connect, backend
):
    backend.respond_json(200, {"total": 0, "items": []})

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("list_orders", {})

    assert not result.is_error, text(result)
    assert dict(backend.requests[0].url.params) == {}


@pytest.mark.parametrize(
    "args",
    [
        pytest.param({"status": "SHIPPED"}, id="unknown status"),
        pytest.param({"limit": 0}, id="limit 0"),
        pytest.param({"limit": 101}, id="limit over 100"),
        pytest.param({"offset": -1}, id="negative offset"),
    ],
)
async def test_list_orders_out_of_bounds_input_is_rejected_without_a_backend_call(
    connect, backend, args
):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("list_orders", args)

    assert result.is_error
    assert backend.requests == []


# Every top-level field of the backend's OrderResponse (#15)
ORDER_FIELDS = set(PLACED_ORDER)


async def test_the_order_tools_are_listed_and_none_can_approve_or_reject(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        names = {t.name for t in (await client.list_tools()).tools}
        place = await tool_named(client, "place_order")
        get = await tool_named(client, "get_order_status")
        listing = await tool_named(client, "list_orders")

    assert not {n for n in names if "approve" in n or "reject" in n}

    assert set(place.input_schema["required"]) == {"quoteId"}
    assert set(get.input_schema["required"]) == {"orderId"}
    assert set(listing.input_schema["properties"]) == {"status", "limit", "offset"}
    assert not listing.input_schema.get("required")
    for tool in (place, get):
        assert tool.output_schema is not None
        assert set(tool.output_schema["properties"]) == ORDER_FIELDS
    assert listing.output_schema is not None
    assert set(listing.output_schema["properties"]) == {"total", "items"}

    assert place.annotations is not None and place.description is not None
    assert place.annotations.read_only_hint is False
    assert place.annotations.destructive_hint is False
    assert place.annotations.idempotent_hint is True
    assert place.annotations.open_world_hint is False
    for phrase in (
        "re-checks live price",
        "changes",
        "policy.reasons",
        "PLACED",
        "PENDING_APPROVAL",
        "checkAgainAfterSeconds",
        "get_order_status",
        "not an error",
        "QUOTE_EXPIRED",
        "QUOTE_ALREADY_ORDERED",
        "orderId",
    ):
        assert phrase in place.description, phrase

    for tool in (get, listing):
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.idempotent_hint is True
    assert get.description is not None
    for phrase in ("checkAgainAfterSeconds", "statusHistory", "approverNote"):
        assert phrase in get.description, phrase


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (409, "QUOTE_EXPIRED", "The quote has expired; quote again for fresh prices"),
        (404, "QUOTE_NOT_FOUND", "No quote of this agent with this id"),
        (503, "VALIO_AIMO_UNAVAILABLE", "The Valio Aimo price and availability API is unavailable"),
        (403, "PERMISSION_DENIED", "The agent token lacks the order:place scope"),
    ],
)
async def test_place_order_backend_errors_come_back_as_errors_with_their_codes(
    connect, backend, status, code, message
):
    backend.respond_json(status, error(code, message))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("place_order", {"quoteId": QUOTE_ID})

    assert result.is_error
    assert f"{code}: {message}" in text(result)


async def test_an_unknown_or_other_organisations_order_is_not_found(connect, backend):
    backend.respond_json(404, error("ORDER_NOT_FOUND", "Order not found"))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_order_status", {"orderId": ORDER_ID})

    assert result.is_error
    assert "ORDER_NOT_FOUND: Order not found" in text(result)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("status",), "SHIPPED"),
        (("statusHistory", 0, "status"), "SHIPPED"),
        (("policy", "outcome"), "MAYBE"),
    ],
)
async def test_a_status_or_outcome_the_tool_does_not_know_fails_loudly(
    connect, backend, path, value
):
    order = json.loads(json.dumps(PLACED_ORDER))
    target = order
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    backend.respond_json(201, order)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("place_order", {"quoteId": QUOTE_ID})

    assert result.is_error
    assert "BACKEND_CONTRACT_MISMATCH" in text(result)


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("place_order", {"quoteId": QUOTE_ID}),
        ("get_order_status", {"orderId": ORDER_ID}),
        ("list_orders", {}),
    ],
)
async def test_missing_key_is_an_error_and_backend_is_not_called(connect, backend, tool, args):
    async with connect() as client:
        result = await client.call_tool(tool, args)

    assert result.is_error
    assert "MISSING_AGENT_KEY" in text(result)
    assert backend.requests == []


async def test_server_instructions_describe_place_then_poll_and_that_agents_cannot_approve(
    connect,
):
    async with connect({"X-Agent-Key": "k1"}) as client:
        instructions = client.instructions

    assert instructions is not None
    for phrase in ("place_order", "get_order_status", "checkAgainAfterSeconds", "list_orders"):
        assert phrase in instructions, phrase
    assert "never approve" in instructions
