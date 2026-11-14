"""
POST /api/v1/products/{code}/substitutes, exercised over HTTP on the fake Valio Aimo API.
"""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.audit.models import AuditEvent
from saint_elmo_backend.catalog.enums import AllergenContainment
from saint_elmo_backend.catalog.models import Product, ProductSubstitution
from saint_elmo_backend.catalog.tests.factories import make_product
from saint_elmo_backend.quotes.tests.conftest import DAIRY_RESTOCK
from saint_elmo_backend.quotes.tests.test_quotes_api import HOSPITAL_KITCHEN
from saint_elmo_backend.substitutes.tests.conftest import LACTOSE_FREE, Authenticate
from saint_elmo_backend.valio_aimo.testing import EILA_10L, UNKNOWN_PRODUCT, FakeValioAimoApi

# A Monday far enough ahead that no closing time has passed
DELIVER_BY = "2030-06-03"
MILK_NEED = {"quantity": 1000, "unit": "L", "deliverBy": DELIVER_BY}


def _url(code: str = EILA_10L) -> str:
    return f"/api/v1/products/{code}/substitutes"


async def _candidate(
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    code: str,
    *,
    litres_per_case: int = 12,
    price_per_litre: str = "1.50",
    curated: bool = False,
    attributes: dict | None = None,
    **live,
) -> None:
    """
    A milk sold per KI of `litres_per_case` 1 l cartons, priced at `price_per_litre`, in
    stock on the requested date unless `live` says otherwise.
    """
    product = await make_product(
        session,
        code=code,
        names={"en": f"Milk {code} 1 l"},
        sales_unit="KI",
        base_unit="ST",
        allowed_lot_size=Decimal("1"),
        units={"ST": Decimal("1"), "KI": Decimal(litres_per_case)},
        **(LACTOSE_FREE | (attributes or {})),
    )
    if curated:
        original = await session.scalar(select(Product).where(Product.code == EILA_10L))
        session.add(ProductSubstitution(product_id=original.id, substitute_id=product.id))
    await session.commit()

    per_litre = float(price_per_litre)
    fake_api.add_product(
        code, value=round(per_litre * litres_per_case, 2), comparison=per_litre, **live
    )


async def _substitutes(client: AsyncClient, code: str = EILA_10L, **request) -> dict:
    response = await client.post(_url(code), json=request)
    assert response.status_code == 200, response.text
    return response.json()


async def test_a_curated_substitute_comes_back_ranked_with_its_offer_for_the_need(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    await _candidate(session, fake_api, "800001", curated=True)
    await authenticate()

    body = await _substitutes(client, **MILK_NEED)

    assert body["deliverBy"] == DELIVER_BY
    assert body["reasonCodes"] == []
    original = body["original"]
    assert original["productCode"] == EILA_10L
    assert original["offer"]["quantity"]["salesUnits"] == 50.0

    [candidate] = body["candidates"]
    assert candidate["rank"] == 1
    assert candidate["tier"] == "BEST"
    assert candidate["curated"] is True
    assert candidate["productCode"] == "800001"
    assert candidate["name"] == "Milk 800001 1 l"
    # 1,000 L in 12 l cases: 83.3, rounded up to 84
    assert candidate["offer"]["quantity"]["salesUnits"] == 84.0
    assert candidate["offer"]["quantity"]["delivered"] == {"value": 1008.0, "unit": "L"}


async def test_every_candidate_for_the_hospital_is_declared_free_from_milk_and_gluten(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    await _candidate(session, fake_api, "800001")
    for code, allergens in [
        ("800002", {"AM": AllergenContainment.CONTAINS, "AW": AllergenContainment.FREE_FROM}),
        ("800003", {"AM": AllergenContainment.FREE_FROM, "AW": AllergenContainment.MAY_CONTAIN}),
        # No declaration for gluten is unknown, never free from it
        ("800004", {"AM": AllergenContainment.FREE_FROM}),
    ]:
        await _candidate(session, fake_api, code, attributes={"allergens": allergens})
    await authenticate(HOSPITAL_KITCHEN)

    # Small enough to stay within the mandate's order limits
    body = await _substitutes(client, quantity=100, unit="L", deliverBy=DELIVER_BY, limit=10)

    [candidate] = body["candidates"]
    assert candidate["productCode"] == "800001"
    preview = candidate["policyPreview"]
    assert preview["outcome"] == "NEEDS_HUMAN"
    assert "SUBSTITUTE_NEEDS_APPROVAL" in [r["code"] for r in preview["reasons"]]


async def test_request_filters_narrow_the_candidates(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    await _candidate(session, fake_api, "800001")
    await _candidate(session, fake_api, "800002", attributes={"labels": ["EU_ORGANIC_FARMING"]})
    await authenticate()

    body = await _substitutes(client, **MILK_NEED, limit=10, requiredLabels=["EU_ORGANIC_FARMING"])

    assert [c["productCode"] for c in body["candidates"]] == ["800002"]
    assert body["candidates"][0]["tradeOffs"]["labelsGained"] == ["EU_ORGANIC_FARMING"]


async def test_no_request_field_drops_a_mandate_requirement(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    # The dairy mandate requires FREE_FROM LACTOSE, which this milk doesn't declare
    await _candidate(session, fake_api, "800001", attributes={"claims": []})
    await _candidate(session, fake_api, "800002")
    await authenticate()

    body = await _substitutes(
        client,
        **MILK_NEED,
        limit=10,
        requiredClaims=[],
        # Not a field: ignored, never a way round the mandate
        allergenStrictness="contains",
        mandate={"requiredClaims": []},
    )

    assert [c["productCode"] for c in body["candidates"]] == ["800002"]
    assert body["candidates"][0]["tradeOffs"]["claimsKept"] == [
        {"type": "FREE_FROM", "element": "LACTOSE"}
    ]


async def test_candidates_that_cant_be_expressed_in_the_buyer_unit_are_left_out(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    await _candidate(session, fake_api, "800001")
    # Sold by weight: the catalog has no litres for it
    await make_product(
        session,
        code="800002",
        names={"en": "Quark 2 kg"},
        sales_unit="KI",
        allowed_lot_size=Decimal("1"),
        **LACTOSE_FREE,
    )
    await session.commit()
    fake_api.add_product("800002", value=8.0, comparison=4.0, comparison_unit="KG")
    # Litres in its name, but priced per kilogram live, so litres can't be converted
    await _candidate(session, fake_api, "800003", comparison_unit="KG")
    await authenticate()

    body = await _substitutes(client, **MILK_NEED, limit=10)

    assert [c["productCode"] for c in body["candidates"]] == ["800001"]


async def test_candidates_are_ranked_with_their_trade_offs_and_policy_preview(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    # The original is 31.31 € per 20 l case: 1.5655 €/L, on time
    await _candidate(session, fake_api, "800001", price_per_litre="1.50")
    await _candidate(session, fake_api, "800002", price_per_litre="1.80")
    # The cheapest, but 3 days late
    await _candidate(session, fake_api, "800003", price_per_litre="1.40", delay=timedelta(days=3))
    await authenticate()

    # 50 cases of 12 l, within the mandate's auto-approve limit
    body = await _substitutes(client, **(MILK_NEED | {"quantity": 600}))

    candidates = body["candidates"]
    assert [(c["productCode"], c["rank"], c["tier"]) for c in candidates] == [
        ("800001", 1, "BEST"),
        ("800002", 2, "BETTER"),
        ("800003", 3, "GOOD"),
    ]
    # On time 40 + price 30 * 1.40 / 1.50; the late one only covers: 20 + 30
    assert [c["score"] for c in candidates] == [68.0, 63.33, 50.0]

    best, pricier, late = candidates
    assert best["tradeOffs"]["pricePerBuyerUnitDeltaPct"] == -4.18
    assert best["tradeOffs"]["earliestDateDelta"] == 0
    assert best["policyPreview"]["outcome"] == "AUTO_APPROVE"

    # 1.80 against 1.5655 €/L is 14.98% more, over the mandate's 10%
    assert pricier["tradeOffs"]["pricePerBuyerUnitDeltaPct"] == 14.98
    assert pricier["policyPreview"]["outcome"] == "NEEDS_HUMAN"
    increase = next(
        r for r in pricier["policyPreview"]["reasons"] if r["code"] == "SUBSTITUTE_PRICE_INCREASE"
    )
    assert increase["facts"]["increasePct"] == 14.98
    assert increase["facts"]["maxIncreasePct"] == 10.0

    assert late["tradeOffs"]["earliestDateDelta"] == 3
    assert "LATE_DELIVERY" in [r["code"] for r in late["policyPreview"]["reasons"]]


async def test_live_offers_are_fetched_only_for_the_first_50_candidates(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    codes = [f"8001{i:02}" for i in range(52)]
    for code in codes:
        await _candidate(session, fake_api, code)
    await authenticate()

    body = await _substitutes(client, **MILK_NEED, limit=10)

    priced = {
        product
        for request in fake_api.requests
        if request.url in ("/api/price", "/api/availability")
        for product in request.json["products"]
    }
    # Equally reliable (no data), so the first 50 by code
    assert priced == {EILA_10L, *codes[:50]}
    assert len(body["candidates"]) == 10


async def test_an_unknown_product_is_product_not_found(
    client: AsyncClient, authenticate: Authenticate
):
    await authenticate()

    response = await client.post(_url(UNKNOWN_PRODUCT), json=MILK_NEED)

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


async def test_unknown_filter_codes_are_named_by_request_field(
    client: AsyncClient, authenticate: Authenticate
):
    await authenticate()

    response = await client.post(
        _url(), json=MILK_NEED | {"requiredLabels": ["NOT_A_LABEL"], "excludedAllergens": ["ZZ"]}
    )

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "UNKNOWN_CODE"
    assert "requiredLabels=[NOT_A_LABEL]" in error["message"]
    assert "excludedAllergens=[ZZ]" in error["message"]


async def test_no_candidates_is_an_empty_answer_with_a_reason_code(
    client: AsyncClient, authenticate: Authenticate
):
    await authenticate()

    body = await _substitutes(client, **MILK_NEED)

    assert body["candidates"] == []
    assert body["reasonCodes"] == ["NO_SUBSTITUTES_FOUND"]
    assert body["original"]["productCode"] == EILA_10L


async def test_origins_outside_the_mandate_find_nothing_rather_than_widening_it(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    await _candidate(session, fake_api, "800001", attributes={"country_of_origin": "fi"})
    await authenticate(replace(DAIRY_RESTOCK, allowed_countries_of_origin=("fi",)))

    body = await _substitutes(client, **MILK_NEED, countriesOfOrigin=["SE"])

    assert body["candidates"] == []
    assert body["reasonCodes"] == ["NO_SUBSTITUTES_FOUND"]


async def test_the_agent_token_needs_the_offers_read_scope(
    client: AsyncClient, authenticate: Authenticate
):
    await authenticate(scopes=(Scope.QUOTE_CREATE,))

    response = await client.post(_url(), json=MILK_NEED)

    assert response.status_code == 403, response.text


async def test_a_curated_substitute_ranks_first_among_equals(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    await _candidate(session, fake_api, "800001")
    await _candidate(session, fake_api, "800002", curated=True)
    await authenticate()

    body = await _substitutes(client, **MILK_NEED)

    assert [(c["productCode"], c["curated"]) for c in body["candidates"]] == [
        ("800002", True),
        ("800001", False),
    ]
    assert body["candidates"][0]["score"] == body["candidates"][1]["score"]


async def test_the_request_is_audited_with_the_candidates_and_their_ranks(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    await _candidate(session, fake_api, "800001", price_per_litre="1.40")
    await _candidate(session, fake_api, "800002")
    await authenticate()

    await _substitutes(client, **MILK_NEED, limit=1)

    [event] = (
        await session.scalars(
            select(AuditEvent).where(AuditEvent.event_type == AuditEventType.SUBSTITUTES_REQUESTED)
        )
    ).all()
    payload = event.payload
    assert event.agent_id is not None
    assert payload["productCode"] == EILA_10L
    assert payload["request"]["quantity"] == 1000.0
    assert payload["deliverBy"] == DELIVER_BY
    assert payload["mandateVersion"] == 1
    assert payload["pricedCandidates"] == ["800001", "800002"]
    [candidate] = payload["candidates"]
    assert candidate["rank"] == 1
    assert candidate["tier"] == "BEST"
    assert candidate["productCode"] == "800001"
    assert candidate["policyPreview"]["outcome"] == "AUTO_APPROVE"


async def test_without_a_quantity_candidates_compare_in_the_originals_comparison_unit(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    await _candidate(session, fake_api, "800001", price_per_litre="1.50")
    await authenticate()

    body = await _substitutes(client, deliverBy=DELIVER_BY)

    assert body["buyerUnit"] == "L"
    assert body["original"]["offer"]["quantity"] is None
    [candidate] = body["candidates"]
    assert candidate["offer"]["quantity"] is None
    # Per litre: 1.50 against 1.5655
    assert candidate["tradeOffs"]["pricePerBuyerUnitDeltaPct"] == -4.18


async def test_blocked_vendors_and_categories_are_never_candidates(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    await _candidate(session, fake_api, "800001")
    await _candidate(session, fake_api, "800002", attributes={"vendor": "Blocked Dairy Oy"})
    # Curated, but in a blocked category
    await _candidate(session, fake_api, "800003", curated=True, attributes={"category": "10500"})
    await authenticate(
        replace(
            DAIRY_RESTOCK,
            allowed_category_codes=(),
            blocked_category_codes=("10500",),
            blocked_vendors=("Blocked Dairy Oy",),
        )
    )

    body = await _substitutes(client, **MILK_NEED, limit=10)

    assert [c["productCode"] for c in body["candidates"]] == ["800001"]
    priced = {p for request in fake_api.requests for p in request.json["products"]}
    assert priced == {EILA_10L, "800001"}


async def test_a_substitute_outside_the_allowed_categories_comes_back_for_a_human_to_decide(
    client: AsyncClient,
    session: AsyncSession,
    fake_api: FakeValioAimoApi,
    authenticate: Authenticate,
):
    # The dairy mandate allows only its dairy category
    await _candidate(session, fake_api, "800001", curated=True, attributes={"category": "10500"})
    await authenticate()

    body = await _substitutes(client, quantity=100, unit="L", deliverBy=DELIVER_BY)

    [candidate] = body["candidates"]
    assert candidate["productCode"] == "800001"
    preview = candidate["policyPreview"]
    assert preview["outcome"] == "NEEDS_HUMAN"
    assert "CATEGORY_NOT_ALLOWED" in [r["code"] for r in preview["reasons"]]
