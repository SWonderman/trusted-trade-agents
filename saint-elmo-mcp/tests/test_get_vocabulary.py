from conftest import text, tool_named

VOCABULARIES = {"claims", "diets", "labels", "allergens", "categories"}


def gs1(code: str, name: str | None, definition: str | None = None) -> dict:
    return {"code": code, "name": name, "definition": definition}


# As the backend serialises GET /api/v1/catalog/vocabulary (#6)
VOCABULARY = {
    "claims": [
        {
            "type": gs1("FREE_FROM", "Free from", "Product is free from the element."),
            "element": gs1("LACTOSE", "Lactose"),
            "productCount": 412,
        },
        {
            "type": gs1("FREE_FROM", "Free from"),
            # A code the data uses but GS1 doesn't list
            "element": gs1("LAKTOOSI", None),
            "productCount": 3,
        },
    ],
    "diets": [{**gs1("VEGAN", "Vegan", "No animal products."), "productCount": 120}],
    "labels": [{**gs1("EU_ORGANIC_FARMING", "EU organic farming"), "productCount": 88}],
    "allergens": [
        {
            **gs1("AM", "Milk"),
            "productCount": 900,
            "statusCounts": {"contains": 700, "mayContain": 50, "undeclared": 0, "freeFrom": 150},
        },
        {
            **gs1("XX", None),
            "productCount": 1,
            "statusCounts": {"contains": 1, "mayContain": 0, "undeclared": 0, "freeFrom": 0},
        },
    ],
    "categories": [{"code": "101010", "productCount": 230}],
}


async def test_get_vocabulary_is_listed_with_an_output_schema_for_all_five_vocabularies(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        tool = await tool_named(client, "get_vocabulary")

    assert tool.output_schema is not None
    assert set(tool.output_schema["properties"]) == VOCABULARIES
    subset = tool.input_schema["properties"]["vocabularies"]["anyOf"][0]
    assert set(subset["items"]["enum"]) == VOCABULARIES
    assert tool.annotations is not None and tool.description is not None
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.open_world_hint is False
    assert " ".join(tool.description.split()).startswith(
        "Call this before using claim, diet, label, allergen or category filters on "
        "search_products. Only codes that at least one product uses are listed."
    )


async def test_calls_the_vocabulary_endpoint_with_the_agent_token(connect, backend):
    backend.respond_json(200, VOCABULARY)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_vocabulary", {})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "GET"
    assert request.url.raw_path == b"/api/v1/catalog/vocabulary"
    assert request.headers["authorization"] == "Bearer k1"


async def test_all_vocabularies_reach_structured_content_null_names_included(connect, backend):
    backend.respond_json(200, VOCABULARY)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_vocabulary", {})

    assert not result.is_error, text(result)
    assert result.structured_content == VOCABULARY


async def test_a_subset_returns_only_those_vocabularies(connect, backend):
    backend.respond_json(200, VOCABULARY)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_vocabulary", {"vocabularies": ["diets", "allergens"]})

    assert not result.is_error, text(result)
    assert result.structured_content == {
        "diets": VOCABULARY["diets"],
        "allergens": VOCABULARY["allergens"],
    }


async def test_an_unknown_vocabulary_name_is_rejected_before_the_backend(connect, backend):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_vocabulary", {"vocabularies": ["brands"]})

    assert result.is_error
    assert backend.requests == []


async def test_missing_key_is_an_error_and_backend_is_not_called(connect, backend):
    async with connect() as client:
        result = await client.call_tool("get_vocabulary", {})

    assert result.is_error
    assert "MISSING_AGENT_KEY" in text(result)
    assert backend.requests == []


async def test_server_instructions_say_to_get_the_vocabulary_before_filtering(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        instructions = client.instructions

    assert instructions is not None
    assert "get_vocabulary" in instructions


async def test_a_vocabulary_missing_from_the_backend_is_a_contract_mismatch(connect, backend):
    backend.respond_json(200, {k: v for k, v in VOCABULARY.items() if k != "claims"})

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_vocabulary", {"vocabularies": ["diets"]})

    assert result.is_error
    assert "BACKEND_CONTRACT_MISMATCH" in text(result)
    assert "claims" in text(result)


async def test_an_entry_missing_its_name_field_is_a_contract_mismatch(connect, backend):
    diet = {k: v for k, v in VOCABULARY["diets"][0].items() if k != "name"}
    backend.respond_json(200, {**VOCABULARY, "diets": [diet]})

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_vocabulary", {})

    assert result.is_error
    assert "BACKEND_CONTRACT_MISMATCH" in text(result)


async def test_an_empty_subset_is_rejected_before_the_backend(connect, backend):
    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_vocabulary", {"vocabularies": []})

    assert result.is_error
    assert backend.requests == []
