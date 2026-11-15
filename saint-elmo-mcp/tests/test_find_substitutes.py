import json
import re

import pytest
from conftest import error, text, tool_named
from test_get_offers import DELIVER_BY, MILK_OFFER

from saint_elmo_mcp.schemas import SHORTFALL_CODES

# The original falls short: not all of the 1000 L asked for is in stock (#16)
SHORT_ORIGINAL_OFFER = {
    **MILK_OFFER,
    "productCode": "463038",
    "reasonCodes": ["PARTIAL_AVAILABILITY"],
}


def candidate(rank: int, tier: str, code: str, **overrides) -> dict:
    return {
        "rank": rank,
        "tier": tier,
        "score": 87.5 - rank,
        "curated": False,
        "productCode": code,
        "name": f"Lactose-free milk {code}",
        "offer": {**MILK_OFFER, "productCode": code, "name": f"Lactose-free milk {code}"},
        "tradeOffs": {
            "pricePerBuyerUnitDeltaPct": 4.2,
            "earliestDateDelta": 0,
            "reliabilityDelta": -0.01,
            "claimsKept": [{"type": "FREE_FROM", "element": "LACTOSE"}],
            "claimsLost": [],
            "labelsGained": ["EU_ORGANIC_FARMING"],
            "labelsLost": [],
            "carbonFootprintDelta": {"value": -0.1, "basis": "PRODUCT_GROUP_AVERAGE"},
        },
        "policyPreview": {"outcome": "AUTO_APPROVE", "reasons": []},
        **overrides,
    }


# As the backend answers for dairy-restock (#16): three ranked candidates, the best a
# curated substitute that needs approval under ALWAYS_NEEDS_APPROVAL
SUBSTITUTES = {
    "original": {
        "productCode": "463038",
        "name": "Valio Eila semi skimmed milk drink 10 l novobox lactose free",
        "offer": SHORT_ORIGINAL_OFFER,
    },
    "deliverBy": DELIVER_BY,
    "buyerUnit": "L",
    "evaluatedAt": "2026-11-14T10:00:01Z",
    "candidates": [
        candidate(
            1,
            "BEST",
            "463040",
            curated=True,
            policyPreview={
                "outcome": "NEEDS_HUMAN",
                "reasons": [
                    {
                        "code": "SUBSTITUTE_NEEDS_APPROVAL",
                        "severity": "NEEDS_HUMAN",
                        "lineRef": "1",
                        "message": "The mandate needs a human to approve every substitute.",
                        "facts": {"substitutesFor": "463038"},
                    }
                ],
            },
        ),
        candidate(2, "BETTER", "463041"),
        candidate(
            3,
            "GOOD",
            "463042",
            tradeOffs={
                "pricePerBuyerUnitDeltaPct": None,
                "earliestDateDelta": None,
                "reliabilityDelta": None,
                "claimsKept": [],
                "claimsLost": [{"type": "FREE_FROM", "element": "LACTOSE"}],
                "labelsGained": [],
                "labelsLost": [],
                "carbonFootprintDelta": None,
            },
        ),
    ],
    "reasonCodes": [],
}

NO_SUBSTITUTES = {
    **SUBSTITUTES,
    "candidates": [],
    "reasonCodes": ["NO_SUBSTITUTES_FOUND"],
}


async def test_find_substitutes_is_listed_with_input_and_output_schemas(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        tool = await tool_named(client, "find_substitutes")

    assert tool.input_schema["required"] == ["code"]
    assert {
        "code",
        "quantity",
        "unit",
        "deliverBy",
        "requiredClaims",
        "requiredLabels",
        "requiredDiets",
        "excludedAllergens",
        "countriesOfOrigin",
        "minDeliveryReliability",
        "limit",
        "language",
    } == set(tool.input_schema["properties"])
    assert tool.output_schema is not None
    assert {
        "original",
        "deliverBy",
        "buyerUnit",
        "evaluatedAt",
        "candidates",
        "reasonCodes",
    } == set(tool.output_schema["properties"])
    assert tool.annotations is not None and tool.description is not None
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.open_world_hint is False
    for phrase in (
        "shortfall",
        "never loosen",
        "policyPreview",
        "not a commitment",
        "substitutesFor",
        "rationale",
        "product-group estimate",
        "NO_SUBSTITUTES_FOUND",
        "get_vocabulary",
    ):
        assert phrase in tool.description, phrase


async def test_server_instructions_send_quote_and_order_shortfalls_to_find_substitutes(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        instructions = client.instructions

    assert instructions is not None
    steps = re.split(r"\n\d+\. ", instructions)
    step = " ".join(next(s for s in steps if s.startswith("find_substitutes:")).split())
    for code in SHORTFALL_CODES:
        assert code in step, code
    assert "create_quote or place_order line" in step


async def test_ranked_candidates_come_back_with_trade_offs_and_policy_preview(
    connect, backend
):
    backend.respond_json(200, SUBSTITUTES)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "find_substitutes",
            {"code": "463038", "quantity": 1000, "unit": "L", "deliverBy": DELIVER_BY},
        )

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "POST"
    assert request.url.path == "/api/v1/products/463038/substitutes"
    assert request.headers["authorization"] == "Bearer k1"
    assert json.loads(request.content) == {
        "quantity": 1000,
        "unit": "L",
        "deliverBy": DELIVER_BY,
    }

    out = result.structured_content
    assert out["buyerUnit"] == "L"
    assert out["evaluatedAt"] == "2026-11-14T10:00:01Z"
    assert out["deliverBy"] == DELIVER_BY
    assert out["original"]["offer"]["reasonCodes"] == ["PARTIAL_AVAILABILITY"]
    assert [(c["rank"], c["tier"], c["score"]) for c in out["candidates"]] == [
        (1, "BEST", 86.5),
        (2, "BETTER", 85.5),
        (3, "GOOD", 84.5),
    ]
    best = out["candidates"][0]
    assert best["curated"] is True
    assert best["policyPreview"]["outcome"] == "NEEDS_HUMAN"
    assert best["policyPreview"]["reasons"][0]["code"] == "SUBSTITUTE_NEEDS_APPROVAL"
    assert best["tradeOffs"]["carbonFootprintDelta"] == {
        "value": -0.1,
        "basis": "PRODUCT_GROUP_AVERAGE",
    }
    assert best["offer"]["quantity"]["salesUnits"] == 50.0
    assert out["candidates"][2]["tradeOffs"]["claimsLost"] == [
        {"type": "FREE_FROM", "element": "LACTOSE"}
    ]
    assert out["reasonCodes"] == []


async def test_filters_and_language_are_forwarded_and_the_code_is_url_encoded(
    connect, backend
):
    backend.respond_json(200, SUBSTITUTES)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool(
            "find_substitutes",
            {
                "code": "46/30 38",
                "requiredClaims": [{"type": "FREE_FROM", "element": "LACTOSE"}],
                "requiredLabels": ["EU_ORGANIC_FARMING"],
                "requiredDiets": ["VEGAN"],
                "excludedAllergens": ["AM"],
                "countriesOfOrigin": ["fi"],
                "minDeliveryReliability": 0.95,
                "limit": 10,
                "language": "fi",
            },
        )

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.url.raw_path == b"/api/v1/products/46%2F30%2038/substitutes"
    assert json.loads(request.content) == {
        "requiredClaims": [{"type": "FREE_FROM", "element": "LACTOSE"}],
        "requiredLabels": ["EU_ORGANIC_FARMING"],
        "requiredDiets": ["VEGAN"],
        "excludedAllergens": ["AM"],
        "countriesOfOrigin": ["fi"],
        "minDeliveryReliability": 0.95,
        "limit": 10,
        "language": "fi",
    }


async def test_just_a_code_sends_an_empty_body(connect, backend):
    backend.respond_json(200, SUBSTITUTES)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("find_substitutes", {"code": "463038"})

    assert not result.is_error, text(result)
    assert json.loads(backend.requests[0].content) == {}


@pytest.mark.parametrize(
    "overrides",
    [
        {"limit": 0},
        {"limit": 11},
        {"minDeliveryReliability": -0.01},
        {"minDeliveryReliability": 1.01},
        {"quantity": 0},
        {"countriesOfOrigin": ["FIN"]},
    ],
)
async def test_out_of_bounds_input_is_rejected_without_a_backend_call(
    connect, backend, overrides
):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("find_substitutes", {"code": "463038", **overrides})

    assert result.is_error
    assert backend.requests == []


async def test_no_substitutes_found_is_a_normal_result(connect, backend):
    backend.respond_json(200, NO_SUBSTITUTES)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("find_substitutes", {"code": "463038"})

    assert not result.is_error, text(result)
    assert result.structured_content["candidates"] == []
    assert result.structured_content["reasonCodes"] == ["NO_SUBSTITUTES_FOUND"]


@pytest.mark.parametrize(
    ("status", "code", "message"),
    [
        (404, "PRODUCT_NOT_FOUND", "Product not found"),
        (422, "UNKNOWN_CODE", "Unknown codes: requiredDiets=[CARNIVORE]"),
        (503, "VALIO_AIMO_UNAVAILABLE", "The Valio Aimo price and availability API is unavailable"),
    ],
)
async def test_backend_errors_come_back_as_errors_with_their_codes(
    connect, backend, status, code, message
):
    backend.respond_json(status, error(code, message))

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("find_substitutes", {"code": "463038"})

    assert result.is_error
    assert f"{code}: {message}" in text(result)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("candidates", 0, "tier"), "OKAY"),
        (("candidates", 0, "policyPreview", "outcome"), "MAYBE"),
        (("reasonCodes",), ["SOMETHING_NEW"]),
        (("candidates", 0, "score"), None),
    ],
)
async def test_a_response_the_tool_does_not_know_fails_loudly(connect, backend, path, value):
    body = json.loads(json.dumps(SUBSTITUTES))
    target = body
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    backend.respond_json(200, body)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("find_substitutes", {"code": "463038"})

    assert result.is_error
    assert "BACKEND_CONTRACT_MISMATCH" in text(result)


async def test_missing_key_is_an_error_and_backend_is_not_called(connect, backend):
    async with connect() as client:
        result = await client.call_tool("find_substitutes", {"code": "463038"})

    assert result.is_error
    assert "MISSING_AGENT_KEY" in text(result)
    assert backend.requests == []


async def test_a_unit_without_a_quantity_is_rejected_without_a_backend_call(connect, backend):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("find_substitutes", {"code": "463038", "unit": "L"})

    assert result.is_error
    assert "quantity" in text(result)
    assert backend.requests == []
