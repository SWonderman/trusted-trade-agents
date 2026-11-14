from conftest import MILK_HIT, text, tool_named

SUMMARY = {k: v for k, v in MILK_HIT.items() if k not in ("relevance", "allergens")}
PROVENANCE = {"source": "Valio Aimo static catalog + GS1 Synkka", "catalogSnapshotDate": "2026-11-01"}

# As the backend returns a product with no GS1 data beyond the catalog row (#5)
SPARSE_PRODUCT = {
    **SUMMARY,
    "name": None,
    "brand": None,
    "countryOfOrigin": None,
    "carbonFootprint": None,
    "units": [],
    "claims": [],
    "allergens": [],
    "translations": [],
    "nutrients": [],
    "ingredients": [],
    "packagingLevels": [],
    "deposits": [],
    "producers": [],
    "fishSpecies": [],
    "safetySheets": [],
    "curatedSubstitutes": [],
    "provenance": PROVENANCE,
}


# As the backend serialises a product with every GS1 section (#5)
FULL_PRODUCT = {
    **SUMMARY,
    "allergens": [
        {"code": "AM", "name": "Milk", "containment": "CONTAINS"},
        {"code": "AW", "name": "Cereals containing gluten", "containment": "MAY_CONTAIN"},
        {"code": "AE", "name": "Eggs", "containment": "FREE_FROM"},
        {"code": "AN", "name": "Tree nuts", "containment": "UNDECLARED"},
    ],
    "translations": [{"language": "en", "name": "Milk", "marketingText": "Creamy!"}],
    "nutrients": [
        {
            "code": "FAT",
            "value": 1.5,
            "unit": "GRM",
            "precision": "APPROXIMATELY",
            "basisQuantity": 100,
            "basisUnit": "MLT",
            "dailyValuePercent": None,
            "servingSize": None,
            "servingSizeUnit": None,
        }
    ],
    "ingredients": [
        {
            "sequence": 1,
            "percentage": 99.5,
            "names": {"fi": "maito", "en": "milk"},
            "origins": [{"stage": "MILKING", "country": "246"}],
        },
        {"sequence": 2, "percentage": None, "names": {"fi": "laktaasientsyymi"}, "origins": []},
    ],
    "packagingLevels": [
        {
            "level": "CASE",
            "lengthMm": 300,
            "widthMm": 200,
            "heightMm": 250,
            "grossWeightG": 10400,
            "netWeightG": 10000,
            "volumeValue": 10,
            "volumeUnit": "LTR",
        }
    ],
    "deposits": [{"materialCode": "900123", "quantity": 1, "unit": "ST"}],
    "producers": [{"name": "Valio Oy", "gln": "6408430000000"}],
    "fishSpecies": [],
    "safetySheets": [{"sheetId": "S1", "statements": []}],
    "curatedSubstitutes": [{"code": "463039", "name": "Valio Eila milk drink 1 l"}],
    "provenance": PROVENANCE,
}


async def test_get_product_is_listed_with_a_code_input_and_an_output_schema(connect):
    async with connect({"X-Agent-Key": "k1"}) as client:
        tool = await tool_named(client, "get_product")

    assert "code" in tool.input_schema["required"]
    assert tool.output_schema is not None
    assert {
        "code",
        "salesUnit",
        "allergens",
        "ingredients",
        "nutrients",
        "packagingLevels",
        "deposits",
        "producers",
        "curatedSubstitutes",
        "provenance",
    } <= set(tool.output_schema["properties"])
    assert tool.annotations is not None and tool.description is not None
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.open_world_hint is False
    assert "curated substitutes" in tool.description
    assert "unknown, NOT" in tool.description


async def test_calls_product_detail_with_the_agent_token_and_an_encoded_code(connect, backend):
    backend.respond_json(200, SPARSE_PRODUCT)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_product", {"code": "46/30 38"})

    assert not result.is_error, text(result)
    (request,) = backend.requests
    assert request.method == "GET"
    assert request.url.raw_path == b"/api/v1/products/46%2F30%2038?language=en"
    assert request.headers["authorization"] == "Bearer k1"


async def test_full_product_reaches_structured_content_with_every_section(connect, backend):
    backend.respond_json(200, FULL_PRODUCT)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_product", {"code": "463038"})

    assert not result.is_error, text(result)
    data = result.structured_content
    assert data["code"] == "463038"
    assert data["salesUnit"] == "KI"
    assert data["claims"] == [{"type": "FREE_FROM", "element": "LACTOSE"}]
    for section in (
        "allergens",
        "nutrients",
        "ingredients",
        "packagingLevels",
        "deposits",
        "producers",
        "curatedSubstitutes",
        "provenance",
    ):
        assert data[section] == FULL_PRODUCT[section], section
    for left_out in ("translations", "fishSpecies", "safetySheets", "somethingTheAgentDoesNotNeed"):
        assert left_out not in data


async def test_sparse_product_validates_with_empty_sections(connect, backend):
    backend.respond_json(200, SPARSE_PRODUCT)

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_product", {"code": "463038"})

    assert not result.is_error, text(result)
    data = result.structured_content
    assert data["name"] is None
    assert data["carbonFootprint"] is None
    assert data["allergens"] == []
    assert data["ingredients"] == []
    assert data["curatedSubstitutes"] == []


async def test_unknown_code_is_product_not_found(connect, backend):
    backend.respond_json(
        404,
        {"error": {"code": "PRODUCT_NOT_FOUND", "message": "Product not found", "requestId": "r-9"}},
    )

    async with connect({"X-Agent-Key": "k1"}) as client:
        result = await client.call_tool("get_product", {"code": "nope"})

    assert result.is_error
    assert "PRODUCT_NOT_FOUND: Product not found" in text(result)
    assert "r-9" in text(result)


async def test_missing_key_is_an_error_and_backend_is_not_called(connect, backend):
    async with connect() as client:
        result = await client.call_tool("get_product", {"code": "463038"})

    assert result.is_error
    assert "MISSING_AGENT_KEY" in text(result)
    assert backend.requests == []
