from datetime import date
from decimal import Decimal
from http import HTTPMethod

import pytest

from saint_elmo_backend.httpkit.exceptions import HttpkitConnectionError, HttpkitTimeoutError
from saint_elmo_backend.valio_aimo.client import ValioAimoClient
from saint_elmo_backend.valio_aimo.exceptions import ValioAimoNotConfigured, ValioAimoUnavailable
from saint_elmo_backend.valio_aimo.testing import (
    EILA_10L,
    LATE_PRODUCT,
    PRICE_ERROR_PRODUCT,
    TERMINAL_PRODUCT,
    UNDELIVERABLE_PRODUCT,
    UNKNOWN_PRODUCT,
    FakeValioAimoApi,
    make_fake_client,
)

DELIVERY = date(2026, 11, 16)


class RecordedSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


# Requests


async def test_price_posts_the_documented_request_with_the_api_key() -> None:
    api = FakeValioAimoApi()
    client = make_fake_client(api, api_key="secret")

    await client.price(customer="123", requested_date=DELIVERY, products=[EILA_10L])

    [request] = api.requests
    assert request.method == HTTPMethod.POST
    assert request.url == "/api/price"
    assert request.headers["X-API-Key"] == "secret"
    assert request.json == {
        "customer": "123",
        "requestedDate": "2026-11-16",
        "products": [EILA_10L],
    }


async def test_availability_posts_the_documented_request_with_the_api_key() -> None:
    api = FakeValioAimoApi()
    client = make_fake_client(api, api_key="secret")

    await client.availability(customer="123", requested_date=DELIVERY, products=[EILA_10L])

    [request] = api.requests
    assert request.method == HTTPMethod.POST
    assert request.url == "/api/availability"
    assert request.headers["X-API-Key"] == "secret"
    assert request.json == {
        "customer": "123",
        "requestedDate": "2026-11-16",
        "products": [EILA_10L],
    }


async def test_ping_gets_the_ping_endpoint_with_the_api_key() -> None:
    api = FakeValioAimoApi()
    client = make_fake_client(api, api_key="secret")

    pong = await client.ping()

    [request] = api.requests
    assert (request.method, request.url) == (HTTPMethod.GET, "/api/ping")
    assert request.headers["X-API-Key"] == "secret"
    assert pong == {"message": "pong"}


# Responses


async def test_price_parses_the_response_without_changing_values() -> None:
    client = make_fake_client(FakeValioAimoApi())

    prices = await client.price(customer="123", requested_date=DELIVERY, products=[EILA_10L])

    eila = prices[EILA_10L]
    assert eila.product_id == EILA_10L
    assert eila.quantity == Decimal("1.0")
    assert eila.catalog_price is not None
    assert eila.catalog_price.value == Decimal("39.80")
    assert eila.comparison_price is not None
    assert eila.comparison_price.value == Decimal("1.99")
    assert eila.comparison_unit == "L"
    assert eila.error is False


async def test_price_error_comes_through_as_is() -> None:
    client = make_fake_client(FakeValioAimoApi())

    prices = await client.price(
        customer="123", requested_date=DELIVERY, products=[PRICE_ERROR_PRODUCT]
    )

    failed = prices[PRICE_ERROR_PRODUCT]
    assert failed.error is True
    assert failed.catalog_price is None
    assert failed.comparison_price is None


async def test_terminal_amount_comes_through_as_999999() -> None:
    client = make_fake_client(FakeValioAimoApi())

    availability = await client.availability(
        customer="123", requested_date=DELIVERY, products=[TERMINAL_PRODUCT]
    )

    terminal = availability[TERMINAL_PRODUCT]
    assert terminal.logistic_model == "TERMINAL"
    [line] = terminal.schedule_lines
    assert line.available_amount == Decimal("999999")


async def test_empty_schedule_lines_and_late_dates_come_through_as_is() -> None:
    client = make_fake_client(FakeValioAimoApi())

    availability = await client.availability(
        customer="123",
        requested_date=DELIVERY,
        products=[UNDELIVERABLE_PRODUCT, LATE_PRODUCT],
    )

    assert availability[UNDELIVERABLE_PRODUCT].schedule_lines == []
    [late] = availability[LATE_PRODUCT].schedule_lines
    assert late.available_date == "2026-11-19"
    assert late.sales_block is False


async def test_a_product_the_api_leaves_out_is_absent_from_the_result() -> None:
    client = make_fake_client(FakeValioAimoApi())

    prices = await client.price(
        customer="123", requested_date=DELIVERY, products=[EILA_10L, UNKNOWN_PRODUCT]
    )
    availability = await client.availability(
        customer="123", requested_date=DELIVERY, products=[EILA_10L, UNKNOWN_PRODUCT]
    )

    assert set(prices) == {EILA_10L}
    assert set(availability) == {EILA_10L}


# Batching


async def test_1001_products_are_sent_as_two_batches_and_merged() -> None:
    api = FakeValioAimoApi()
    client = make_fake_client(api)
    fillers = [f"8{n:05d}" for n in range(999)]
    products = [EILA_10L, *fillers, TERMINAL_PRODUCT]

    prices = await client.price(customer="123", requested_date=DELIVERY, products=products)

    first, second = api.requests
    assert first.json is not None and second.json is not None
    assert first.json["products"] == products[:1000]  # type: ignore[index]
    assert second.json["products"] == [TERMINAL_PRODUCT]  # type: ignore[index]
    assert set(prices) == {EILA_10L, TERMINAL_PRODUCT}


async def test_no_products_means_no_request() -> None:
    api = FakeValioAimoApi()
    client = make_fake_client(api)

    assert await client.price(customer="123", requested_date=DELIVERY, products=[]) == {}
    assert api.requests == []


# Retries


async def test_429_then_success_honours_retry_after() -> None:
    api = FakeValioAimoApi()
    api.fail_next(429, retry_after="2")
    sleep = RecordedSleep()
    client = make_fake_client(api, sleep=sleep)

    prices = await client.price(customer="123", requested_date=DELIVERY, products=[EILA_10L])

    assert set(prices) == {EILA_10L}
    assert len(api.requests) == 2
    assert sleep.delays == [2.0]


@pytest.mark.parametrize("status", [500, 501, 503, 507])
async def test_5xx_is_retried_with_exponential_backoff_and_jitter(status: int) -> None:
    api = FakeValioAimoApi()
    api.fail_next(status, times=2)
    sleep = RecordedSleep()
    client = make_fake_client(api, sleep=sleep)

    prices = await client.price(customer="123", requested_date=DELIVERY, products=[EILA_10L])

    assert set(prices) == {EILA_10L}
    assert len(api.requests) == 3
    first, second = sleep.delays
    assert 0.4 <= first <= 0.6
    assert 0.8 <= second <= 1.2


async def test_a_retry_after_shorter_than_the_backoff_waits_the_backoff() -> None:
    api = FakeValioAimoApi()
    api.fail_next(429, retry_after="0")
    sleep = RecordedSleep()
    client = make_fake_client(api, sleep=sleep)

    await client.price(customer="123", requested_date=DELIVERY, products=[EILA_10L])

    [delay] = sleep.delays
    assert 0.4 <= delay <= 0.6


@pytest.mark.parametrize(
    "error",
    [
        HttpkitTimeoutError(message="timed out", method=HTTPMethod.POST, url="/api/price"),
        HttpkitConnectionError(message="refused", method=HTTPMethod.POST, url="/api/price"),
    ],
)
async def test_timeouts_and_connection_errors_are_retried(error: Exception) -> None:
    api = FakeValioAimoApi()
    api.raise_next(error)
    client = make_fake_client(api)

    prices = await client.price(customer="123", requested_date=DELIVERY, products=[EILA_10L])

    assert set(prices) == {EILA_10L}
    assert len(api.requests) == 2


@pytest.mark.parametrize("status", [401, 422])
async def test_other_4xx_fail_straight_away(status: int) -> None:
    api = FakeValioAimoApi()
    api.fail_next(status)
    sleep = RecordedSleep()
    client = make_fake_client(api, sleep=sleep)

    with pytest.raises(ValioAimoUnavailable) as err:
        await client.price(customer="123", requested_date=DELIVERY, products=[EILA_10L])

    assert err.value.status_code == status
    assert len(api.requests) == 1
    assert sleep.delays == []


async def test_a_batch_that_keeps_failing_raises_for_the_whole_call() -> None:
    api = FakeValioAimoApi()
    # The first batch answers; the second fails on all 3 attempts.
    api.fail_next(503, times=3, after=1)
    client = make_fake_client(api)
    fillers = [f"8{n:05d}" for n in range(999)]
    products = [EILA_10L, *fillers, TERMINAL_PRODUCT]

    with pytest.raises(ValioAimoUnavailable) as err:
        await client.price(customer="123", requested_date=DELIVERY, products=products)

    assert err.value.status_code == 503
    assert err.value.attempts == 3
    assert len(api.requests) == 4


# Configuration


@pytest.mark.parametrize(
    ("api_url", "api_key"),
    [(None, None), ("https://valio-aimo.test", None), (None, "key"), ("", "")],
)
async def test_every_call_without_url_or_key_raises_not_configured(
    api_url: str | None, api_key: str | None
) -> None:
    api = FakeValioAimoApi()
    client = ValioAimoClient(api_url=api_url, api_key=api_key, transport=api)

    with pytest.raises(ValioAimoNotConfigured):
        await client.price(customer="123", requested_date=DELIVERY, products=[EILA_10L])
    with pytest.raises(ValioAimoNotConfigured):
        await client.availability(customer="123", requested_date=DELIVERY, products=[EILA_10L])
    with pytest.raises(ValioAimoNotConfigured):
        await client.ping()
    assert api.requests == []
