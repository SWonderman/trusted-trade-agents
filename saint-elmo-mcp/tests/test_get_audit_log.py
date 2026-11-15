import pytest

from conftest import error, text, tool_named
from test_orders import ORDER_ID
from test_quotes import QUOTE_ID

AGENT = {
    "kind": "agent",
    "id": "1a2b3c4d-5e6f-4a7b-8c9d-0e1f2a3b4c5d",
    "name": "dairy-restock",
}
APPROVER = {
    "kind": "user",
    "id": "9f8e7d6c-5b4a-4392-8170-6f5e4d3c2b1a",
    "name": "Aino Virtanen",
}

# As the backend renders them (#57): one quote that needed a human, then the order
QUOTED = {
    "id": "0b6a1c2d-3e4f-4a5b-8c6d-7e8f9a0b1c2d",
    "at": "2026-11-14T10:00:00Z",
    "type": "QUOTE_CREATED",
    "subjectId": QUOTE_ID,
    "actor": AGENT,
    "summary": "dairy-restock quoted 50 KI of 463038 for €1,565.50: needs a human "
    "(over the auto-approve limit)",
    "outcome": "NEEDS_HUMAN",
    "reasonCodes": ["OVER_AUTO_APPROVE_LIMIT"],
    "payload": {"quoteId": QUOTE_ID, "policy": {"outcome": "NEEDS_HUMAN"}},
}
PENDING = {
    "id": "1c7b2d3e-4f5a-4b6c-9d7e-8f9a0b1c2d3e",
    "at": "2026-11-14T10:05:00Z",
    "type": "ORDER_PENDING_APPROVAL",
    "subjectId": ORDER_ID,
    "actor": AGENT,
    "summary": "dairy-restock's order waits for a human's approval",
    "outcome": None,
    "reasonCodes": None,
    "payload": {"orderId": ORDER_ID},
}
APPROVED = {
    "id": "2d8c3e4f-5a6b-4c7d-8e8f-9a0b1c2d3e4f",
    "at": "2026-11-14T11:00:00Z",
    "type": "ORDER_APPROVED",
    "subjectId": ORDER_ID,
    "actor": APPROVER,
    "summary": 'Aino Virtanen approved dairy-restock\'s order: "Fine this once"',
    "outcome": None,
    "reasonCodes": None,
    "payload": {"orderId": ORDER_ID, "note": "Fine this once"},
}

TRAIL = {"orderId": ORDER_ID, "items": [QUOTED, PENDING, APPROVED]}


def without_payload(event: dict) -> dict:
    return {k: v for k, v in event.items() if k not in {"payload", "id"}}


async def test_get_order_trail_reads_the_whole_trail_oldest_first_without_payloads(
    connect, backend
):
    backend.respond_json(200, TRAIL)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_order_trail", {"order_id": ORDER_ID})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "GET"
    assert request.url.path == f"/api/v1/orders/{ORDER_ID}/trail"
    assert request.url.query == b""
    assert request.headers["authorization"] == "Bearer k1"
    assert result.structured_content == {
        "orderId": ORDER_ID,
        "items": [
            without_payload(QUOTED),
            without_payload(PENDING),
            without_payload(APPROVED),
        ],
    }


async def test_get_order_trail_include_payload_returns_the_recorded_data(
    connect, backend
):
    backend.respond_json(200, TRAIL)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "get_order_trail", {"order_id": ORDER_ID, "include_payload": True}
        )

    assert [e["payload"] for e in result.structured_content["items"]] == [
        QUOTED["payload"],
        PENDING["payload"],
        APPROVED["payload"],
    ]


@pytest.mark.parametrize(
    ("status", "body", "code"),
    [
        (404, error("ORDER_NOT_FOUND", "Order not found"), "ORDER_NOT_FOUND"),
        (
            403,
            error("PERMISSION_DENIED", "The Agent token lacks the `audit:read` scope"),
            "PERMISSION_DENIED",
        ),
    ],
)
async def test_get_order_trail_backend_errors_come_back_with_their_codes(
    connect, backend, status, body, code
):
    backend.respond_json(status, body)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_order_trail", {"order_id": ORDER_ID})

    assert result.is_error
    assert f"{code}: " in text(result)


async def test_get_audit_log_lists_own_events_newest_first_with_default_limit(
    connect, backend
):
    backend.respond_json(200, {"items": [APPROVED, PENDING], "nextCursor": "c-2"})

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_audit_log", {})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "GET"
    assert request.url.path == "/api/v1/audit-events"
    assert dict(request.url.params) == {"limit": "20"}
    assert request.headers["authorization"] == "Bearer k1"
    assert result.structured_content == {
        "items": [without_payload(APPROVED), without_payload(PENDING)],
        "nextCursor": "c-2",
    }


async def test_get_audit_log_sends_its_filters_to_the_backend_query(connect, backend):
    backend.respond_json(200, {"items": [], "nextCursor": None})

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "get_audit_log",
            {
                "event_type": "ORDER_APPROVED",
                "since": "2026-11-14T00:00:00+02:00",
                "cursor": "c-2",
                "limit": 5,
            },
        )

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert dict(request.url.params) == {
        "type": "ORDER_APPROVED",
        "from": "2026-11-14T00:00:00+02:00",
        "cursor": "c-2",
        "limit": "5",
    }


async def test_get_audit_log_include_payload_returns_the_recorded_data(
    connect, backend
):
    backend.respond_json(200, {"items": [APPROVED], "nextCursor": None})

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_audit_log", {"include_payload": True})

    assert result.structured_content["items"] == [
        {k: v for k, v in APPROVED.items() if k != "id"}
    ]


@pytest.mark.parametrize("limit", [0, 201])
async def test_get_audit_log_limit_outside_1_to_200_is_rejected_without_a_backend_call(
    connect, backend, limit
):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_audit_log", {"limit": limit})

    assert result.is_error
    assert backend.requests == []


@pytest.mark.parametrize(
    ("status", "body", "code"),
    [
        (
            403,
            error("PERMISSION_DENIED", "The Agent token lacks the `audit:read` scope"),
            "PERMISSION_DENIED",
        ),
        (
            422,
            error("VALIDATION_ERROR", "The cursor is not one this list returned"),
            "VALIDATION_ERROR",
        ),
    ],
)
async def test_get_audit_log_backend_errors_come_back_with_their_codes(
    connect, backend, status, body, code
):
    backend.respond_json(status, body)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_audit_log", {"cursor": "stale"})

    assert result.is_error
    assert f"{code}: " in text(result)


EVENT_FIELDS = {
    "type",
    "at",
    "subjectId",
    "actor",
    "summary",
    "outcome",
    "reasonCodes",
    "payload",
}


async def test_both_tools_are_listed_read_only_with_their_own_schemas(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        trail = await tool_named(client, "get_order_trail")
        log = await tool_named(client, "get_audit_log")

    assert set(trail.input_schema["properties"]) == {"order_id", "include_payload"}
    assert trail.input_schema["required"] == ["order_id"]
    assert set(trail.output_schema["properties"]) == {"orderId", "items"}

    assert set(log.input_schema["properties"]) == {
        "event_type",
        "since",
        "cursor",
        "limit",
        "include_payload",
    }
    assert log.input_schema["properties"]["limit"]["default"] == 20
    assert log.input_schema["properties"]["limit"]["maximum"] == 200
    assert set(log.output_schema["properties"]) == {"items", "nextCursor"}

    for tool in (trail, log):
        assert tool.input_schema["properties"]["include_payload"]["default"] is False
        assert (
            set(tool.output_schema["$defs"]["AuditEvent"]["properties"]) == EVENT_FIELDS
        )
        assert tool.annotations.read_only_hint
        assert tool.annotations.idempotent_hint
        assert tool.annotations.open_world_hint is False
