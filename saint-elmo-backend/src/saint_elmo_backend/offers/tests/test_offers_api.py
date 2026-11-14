"""
POST /api/v1/offers, exercised over HTTP on the fake Valio Aimo API.
"""

import pytest
from httpx import AsyncClient

from saint_elmo_backend.accounts.models import Organization
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.agents.tests.factories import bearer, issue_token, make_agent
from saint_elmo_backend.valio_aimo.testing import (
    BLOCKED_PRODUCT,
    EILA_10L,
    LATE_PRODUCT,
    PRICE_ERROR_PRODUCT,
    TERMINAL_PRODUCT,
    UNDELIVERABLE_PRODUCT,
    FakeValioAimoApi,
)

OFFERS_URL = "/api/v1/offers"
# Far enough ahead that no closing time has passed
DELIVER_BY = "2030-06-03"


def _item(body: dict, code: str) -> dict:
    return next(item for item in body["items"] if item["productCode"] == code)


async def test_the_milk_example_converts_1000_litres_to_50_cases(scripted_products, client):
    response = await client.post(
        OFFERS_URL,
        json={
            "deliverBy": DELIVER_BY,
            "items": [{"productCode": "463038", "quantity": 1000, "unit": "L"}],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["deliverBy"] == DELIVER_BY
    assert "evaluatedAt" in body

    item = _item(body, "463038")
    assert item["name"] == "Valio Eila® semi skimmed milk drink 10 l novobox lactose free"
    assert item["salesUnit"] == "KI"
    assert item["price"]["perSalesUnit"] == {"net": 31.31, "gross": 35.69}
    assert item["price"]["comparisonPrice"] == {"value": 1.57, "unit": "L"}
    assert item["price"]["currency"] == "EUR"
    assert item["price"]["taxRate"] == 14.0
    assert item["price"]["customerSpecific"] is False

    quantity = item["quantity"]
    assert quantity["requested"] == {"value": 1000.0, "unit": "L"}
    assert quantity["conversion"] == {
        "perSalesUnit": {"value": 20.0, "unit": "L"},
        "basis": "PRICE_COMPARISON",
        "crossCheck": "AGREES",
    }
    assert quantity["salesUnits"] == 50.0
    assert quantity["lotSize"] == 1.0
    assert quantity["roundedUp"] is False
    assert quantity["delivered"] == {"value": 1000.0, "unit": "L"}
    assert quantity["lineTotal"] == {"net": 1565.5, "gross": 1784.5}

    assert item["deliveryReliability"] == 0.982
    assert item["carbonFootprint"] == {"value": 1.1, "basis": "PRODUCT_GROUP_AVERAGE"}
    assert item["provenance"]["cached"] is False


async def _offers(client: AsyncClient, *items: dict, deliver_by: str = DELIVER_BY) -> dict:
    response = await client.post(OFFERS_URL, json={"deliverBy": deliver_by, "items": list(items)})
    assert response.status_code == 200, response.text
    return response.json()


def _requests_to(api: FakeValioAimoApi, url: str) -> list[dict]:
    return [r.json for r in api.requests if r.url == url]  # type: ignore[misc]


async def test_terminal_products_have_an_unknown_amount_never_999999(scripted_products, client):
    body = await _offers(client, {"productCode": TERMINAL_PRODUCT, "quantity": 10})

    item = _item(body, TERMINAL_PRODUCT)
    assert item["availability"]["logisticModel"] == "TERMINAL"
    assert item["availability"]["availableAmount"] is None
    assert item["availability"]["availableAmountKnown"] is False
    assert item["availability"]["meetsDeadline"] is True
    assert item["quantity"]["coveredByAvailability"] is None
    assert "999999" not in str(body)


async def test_an_earliest_date_after_deliver_by_is_late(scripted_products, client):
    body = await _offers(client, {"productCode": LATE_PRODUCT})

    item = _item(body, LATE_PRODUCT)
    assert item["availability"]["earliestDate"] == "2030-06-06"
    assert item["availability"]["meetsDeadline"] is False
    assert item["reasonCodes"] == ["LATE_DELIVERY"]
    assert "quantity" not in item or item["quantity"] is None


async def test_empty_schedule_lines_are_not_deliverable(scripted_products, client):
    body = await _offers(client, {"productCode": UNDELIVERABLE_PRODUCT})

    item = _item(body, UNDELIVERABLE_PRODUCT)
    assert item["availability"]["earliestDate"] is None
    assert item["availability"]["meetsDeadline"] is False
    assert item["reasonCodes"] == ["NOT_DELIVERABLE"]


async def test_known_stock_below_the_quantity_is_partial(scripted_products, client):
    # The late product has 40 KI in stock
    body = await _offers(client, {"productCode": LATE_PRODUCT, "quantity": 50})

    item = _item(body, LATE_PRODUCT)
    assert item["availability"]["availableAmount"] == 40.0
    assert item["quantity"]["coveredByAvailability"] is False
    assert item["reasonCodes"] == ["LATE_DELIVERY", "PARTIAL_AVAILABILITY"]


async def test_sales_blocked_products_say_so(scripted_products, client):
    body = await _offers(client, {"productCode": BLOCKED_PRODUCT})

    item = _item(body, BLOCKED_PRODUCT)
    assert item["availability"]["salesBlocked"] is True
    assert set(item["reasonCodes"]) == {"LATE_DELIVERY", "SALES_BLOCKED"}


async def test_a_passed_closing_time_misses_the_deadline(scripted_products, client):
    # The fake closes ordering two days before the requested date
    body = await _offers(client, {"productCode": EILA_10L}, deliver_by="2024-01-10")

    item = _item(body, EILA_10L)
    assert item["availability"]["meetsDeadline"] is False
    assert item["reasonCodes"] == ["CLOSING_TIME_PASSED"]


async def test_a_price_error_gives_no_price_without_failing_other_items(scripted_products, client):
    body = await _offers(
        client,
        {"productCode": PRICE_ERROR_PRODUCT, "quantity": 3},
        {"productCode": EILA_10L, "quantity": 1000, "unit": "L"},
    )

    unpriced = _item(body, PRICE_ERROR_PRODUCT)
    assert unpriced["price"] is None
    assert unpriced["quantity"]["salesUnits"] == 3.0
    assert unpriced["quantity"]["lineTotal"] is None
    assert unpriced["reasonCodes"] == ["NO_PRICE"]
    assert _item(body, EILA_10L)["quantity"]["lineTotal"] == {"net": 1565.5, "gross": 1784.5}


async def test_litres_without_a_price_cannot_be_converted(scripted_products, client):
    body = await _offers(client, {"productCode": PRICE_ERROR_PRODUCT, "quantity": 5, "unit": "L"})

    item = _item(body, PRICE_ERROR_PRODUCT)
    assert item["quantity"]["salesUnits"] is None
    assert item["quantity"]["lineTotal"] is None
    assert item["reasonCodes"] == ["NO_PRICE", "CONVERSION_UNAVAILABLE"]


async def test_a_repeated_request_within_price_validity_is_served_from_cache(
    scripted_products, client, fake_api
):
    item = {"productCode": EILA_10L, "quantity": 1000, "unit": "L"}
    first = await _offers(client, item)
    second = await _offers(client, item)

    assert len(_requests_to(fake_api, "/api/price")) == 1
    assert len(_requests_to(fake_api, "/api/availability")) == 1
    assert _item(first, EILA_10L)["provenance"]["cached"] is False
    assert _item(second, EILA_10L)["provenance"]["cached"] is True
    assert _item(second, EILA_10L)["quantity"] == _item(first, EILA_10L)["quantity"]


async def test_only_the_requested_products_are_sent_in_one_batch_for_the_buyer(
    scripted_products, client, fake_api, organization: Organization
):
    await _offers(
        client,
        {"productCode": EILA_10L},
        {"productCode": LATE_PRODUCT},
        {"productCode": EILA_10L, "quantity": 2},
    )

    for url in ("/api/price", "/api/availability"):
        (request,) = _requests_to(fake_api, url)
        assert request["products"] == [EILA_10L, LATE_PRODUCT]
        assert request["customer"] == organization.customer_number
        assert request["requestedDate"] == DELIVER_BY


async def test_items_come_back_in_request_order_including_repeats(scripted_products, client):
    body = await _offers(
        client,
        {"productCode": LATE_PRODUCT},
        {"productCode": EILA_10L},
        {"productCode": LATE_PRODUCT, "quantity": 2},
    )

    assert [item["productCode"] for item in body["items"]] == [LATE_PRODUCT, EILA_10L, LATE_PRODUCT]


async def test_offers_report_their_source_and_validity(scripted_products, client):
    item = _item(await _offers(client, {"productCode": EILA_10L}), EILA_10L)

    provenance = item["provenance"]
    assert provenance["source"] == "Valio Aimo price and availability API"
    assert "fetchedAt" in provenance
    # The closing time comes before the price's validTo
    assert provenance["validUntil"] == item["availability"]["closingTime"]


async def test_unknown_product_codes_are_all_listed(scripted_products, client, fake_api):
    response = await client.post(
        OFFERS_URL,
        json={
            "deliverBy": DELIVER_BY,
            "items": [
                {"productCode": "111111"},
                {"productCode": EILA_10L},
                {"productCode": "222222"},
            ],
        },
    )

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "PRODUCT_NOT_FOUND"
    assert "111111" in error["message"] and "222222" in error["message"]
    assert fake_api.requests == []


async def test_more_than_50_items_is_rejected(scripted_products, client):
    items = [{"productCode": EILA_10L}] * 51
    response = await client.post(OFFERS_URL, json={"deliverBy": DELIVER_BY, "items": items})

    assert response.status_code == 422


async def test_an_unavailable_api_answers_503(scripted_products, client, fake_api):
    fake_api.fail_next(503, times=3)

    response = await client.post(
        OFFERS_URL, json={"deliverBy": DELIVER_BY, "items": [{"productCode": EILA_10L}]}
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "VALIO_AIMO_UNAVAILABLE"


async def test_a_buyer_without_a_customer_number_cannot_be_priced(
    scripted_products, client, session, organization: Organization
):
    organization.customer_number = None
    await session.commit()

    response = await client.post(
        OFFERS_URL, json={"deliverBy": DELIVER_BY, "items": [{"productCode": EILA_10L}]}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CUSTOMER_NUMBER_MISSING"


async def test_the_request_has_no_customer_field(scripted_products, client, fake_api, organization):
    await client.post(
        OFFERS_URL,
        json={"deliverBy": DELIVER_BY, "customer": "C999999", "items": [{"productCode": EILA_10L}]},
    )

    (request,) = _requests_to(fake_api, "/api/price")
    assert request["customer"] == organization.customer_number


@pytest.mark.parametrize("scopes", [[Scope.CATALOG_READ], []])
async def test_agents_need_the_offers_read_scope(
    scripted_products, client, session, organization, scopes
):
    agent = await make_agent(session, organization)
    token = await issue_token(session, agent, scopes=scopes)
    await session.commit()

    response = await client.post(
        OFFERS_URL,
        json={"deliverBy": DELIVER_BY, "items": [{"productCode": EILA_10L}]},
        headers=bearer(token),
    )

    assert response.status_code == 403


async def test_the_endpoint_and_its_errors_are_documented(client):
    operation = (await client.get("/openapi.json")).json()["paths"]["/api/v1/offers"]["post"]

    assert {"200", "401", "403", "404", "409", "422", "503"} <= set(operation["responses"])
    assert operation["security"] == [{"AgentToken": ["offers:read"]}]
