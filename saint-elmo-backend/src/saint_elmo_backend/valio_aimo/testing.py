"""
Shared fake of the Valio Aimo API for the test suite (#12–#16 reuse it).

`FakeValioAimoApi` is an `AsyncTransport` that answers `/api/price`,
`/api/availability` and `/api/ping` like the real API, from a small scripted
catalogue, so a real `ValioAimoClient` (batching, retries, parsing) runs on top of
it. Use `make_fake_client` to get one.

Values and formats are copied from live responses (2026-11-14): title-case
`logisticModel` (`Stock`, `Terminal`), timestamps with a `+0200` offset, amounts as
floats, plain dates only in `availableDate`.

Never wire this into the running app: there is no fallback to fake data.
"""

import json
from collections import deque
from collections.abc import Callable, Mapping
from datetime import date, timedelta
from types import TracebackType
from typing import Any, Self, cast, override

from pydantic import JsonValue

from saint_elmo_backend.httpkit.dataclasses import Request
from saint_elmo_backend.httpkit.response import ResponseWrapper
from saint_elmo_backend.valio_aimo.client import Sleep, ValioAimoClient

# Scripted products

# Valio Eila® semi skimmed milk drink 10 l novobox lactose free, sold per KI (2 × 10 l).
# Live values: catalogPrice / comparisonPrice = 31.31 / 1.57 ≈ 20 L per sales unit,
# delivered as Terminal.
EILA_10L = "463038"
# Delivered from a supplier's warehouse: available amount unknown, reported as 999999.
TERMINAL_PRODUCT = "900001"
# The API found no price for it: `error: true`, no price fields.
PRICE_ERROR_PRODUCT = "900002"
# Empty `scheduleLines`: cannot be delivered on any date.
UNDELIVERABLE_PRODUCT = "900003"
# Deliverable, but only 3 days after the requested date. Stock, so its amount is real.
LATE_PRODUCT = "900004"
# Cannot be ordered right now: `salesBlock` on the product and its schedule line, with
# an available date weeks away (like 463989 live).
BLOCKED_PRODUCT = "900005"
# Stock arriving in two schedule lines: 10 two days before the requested date, 60 on it.
RESTOCKED_PRODUCT = "900006"
# Not in the fake catalogue: the API leaves it out of every response.
UNKNOWN_PRODUCT = "999990"

LATE_PRODUCT_DELAY = timedelta(days=3)
BLOCKED_PRODUCT_DELAY = timedelta(days=42)
# The real API's limit, kept separate from the client's constant on purpose: the fake
# models the API, so a client that stops batching gets the same 422 the API would send.
MAX_PRODUCTS_PER_REQUEST = 1000

FAKE_API_URL = "https://valio-aimo.test"
FAKE_API_KEY = "test-key"

_TIME_NOW = "2026-11-14T10:15:00+0200"
_VALID_FROM = "2026-09-01T00:00:00+0300"
_VALID_TO = "9999-12-31T00:00:00+0200"


def _timestamp(day: date, time: str = "00:00:00") -> str:
    """
    The API's timestamp format, e.g. `2026-11-16T00:00:00+0200`.
    """
    return f"{day.isoformat()}T{time}+0200"


def _price(value: float, value_with_tax: float) -> dict[str, Any]:
    return {
        "value": value,
        "valueWithTax": value_with_tax,
        "validFrom": _VALID_FROM,
        "validTo": _VALID_TO,
        "currency": "EUR",
    }


def _priced(product_id: str, value: float, comparison: float, unit: str) -> dict[str, Any]:
    with_tax = round(value * 1.14, 2)
    return {
        "productId": product_id,
        "quantity": 1.0,
        "catalogPrice": _price(value, with_tax),
        "priceWithTax": {
            "value": with_tax,
            "validFrom": _VALID_FROM,
            "validTo": _VALID_TO,
            "currency": "EUR",
        },
        "comparisonPrice": _price(comparison, round(comparison * 1.14, 2)),
        "comparisonUnit": unit,
        "tax": {"taxRate": 14.0, "taxValue": round(with_tax - value, 2)},
        "listPrice": _price(value, with_tax),
        "netPriceFound": False,
        "error": False,
    }


def _price_error(product_id: str) -> dict[str, Any]:
    return {
        "productId": product_id,
        "quantity": 1.0,
        "catalogPrice": None,
        "priceWithTax": None,
        "comparisonPrice": None,
        "comparisonUnit": None,
        "tax": None,
        "listPrice": None,
        "netPriceFound": False,
        "error": True,
    }


def _available(
    product_id: str,
    *,
    amount: float,
    on: date,
    sales_unit: str = "KI",
    logistic_model: str = "Stock",
    sales_block: bool = False,
) -> dict[str, Any]:
    return {
        "productId": product_id,
        "closingTime": _timestamp(on - timedelta(days=2), "15:00:00"),
        "salesBlock": sales_block,
        "logisticModel": logistic_model,
        "scheduleLines": [
            {
                "salesBlock": sales_block,
                "availableAmount": amount,
                "availableDate": on.isoformat(),
                "salesUnit": sales_unit,
            }
        ],
    }


def _restocked(product_id: str, on: date) -> dict[str, Any]:
    early = on - timedelta(days=2)
    return {
        "productId": product_id,
        "closingTime": _timestamp(early - timedelta(days=1), "15:00:00"),
        "salesBlock": False,
        "logisticModel": "Stock",
        "scheduleLines": [
            {
                "salesBlock": False,
                "availableAmount": 60.0,
                "availableDate": on.isoformat(),
                "salesUnit": "KI",
            },
            {
                "salesBlock": False,
                "availableAmount": 10.0,
                "availableDate": early.isoformat(),
                "salesUnit": "KI",
            },
        ],
    }


def _undeliverable(product_id: str) -> dict[str, Any]:
    # Live, an undeliverable product has no closing time and no logistic model either
    return {
        "productId": product_id,
        "closingTime": None,
        "salesBlock": False,
        "logisticModel": None,
        "scheduleLines": [],
    }


_SCRIPTED_PRICES: dict[str, Callable[[str], dict[str, Any]]] = {
    EILA_10L: lambda p: _priced(p, 31.31, 1.57, "L"),
    TERMINAL_PRODUCT: lambda p: _priced(p, 12.50, 2.50, "KG"),
    PRICE_ERROR_PRODUCT: _price_error,
    UNDELIVERABLE_PRODUCT: lambda p: _priced(p, 8.00, 4.00, "KG"),
    LATE_PRODUCT: lambda p: _priced(p, 8.00, 4.00, "KG"),
    BLOCKED_PRODUCT: lambda p: _priced(p, 5.20, 10.40, "KG"),
    RESTOCKED_PRODUCT: lambda p: _priced(p, 8.00, 4.00, "KG"),
}

_SCRIPTED_AVAILABILITY: dict[str, Callable[[str, date], dict[str, Any]]] = {
    EILA_10L: lambda p, d: _available(p, amount=999999.0, on=d, logistic_model="Terminal"),
    TERMINAL_PRODUCT: lambda p, d: _available(p, amount=999999.0, on=d, logistic_model="Terminal"),
    PRICE_ERROR_PRODUCT: lambda p, d: _available(p, amount=120.0, on=d),
    UNDELIVERABLE_PRODUCT: lambda p, _d: _undeliverable(p),
    RESTOCKED_PRODUCT: _restocked,
    LATE_PRODUCT: lambda p, d: _available(p, amount=40.0, on=d + LATE_PRODUCT_DELAY),
    BLOCKED_PRODUCT: lambda p, d: _available(
        p,
        amount=999999.0,
        on=d + BLOCKED_PRODUCT_DELAY,
        sales_unit="ST",
        logistic_model="Terminal",
        sales_block=True,
    ),
}


# Transport


class FakeResponse(ResponseWrapper):
    def __init__(self, status: int, body: JsonValue, headers: Mapping[str, str] | None = None):
        self._status: int = status
        self._body: str = json.dumps(body)
        self._headers: dict[str, str] = dict(headers or {})

    @override
    def ok(self) -> bool:
        return 200 <= self._status < 300

    @override
    def status_code(self) -> int:
        return self._status

    @override
    def text(self) -> str:
        return self._body

    @override
    def json(self) -> JsonValue:
        return cast(JsonValue, json.loads(self._body))

    @override
    def headers(self) -> dict[str, str]:
        return dict(self._headers)


class FakeValioAimoApi:
    """
    Answers like the Valio Aimo API from the scripted catalogue above.

    - `requests` records every request received, in order.
    - `fail_next(status, ...)` makes the next request(s) fail with that status
      (e.g. 429 with a `Retry-After`) before answering normally again; `after=n`
      lets n requests through first.
    - `raise_next(exc)` makes the next request raise a transport error.
    - More than 1,000 products in one request is rejected with 422, like the API.
    """

    def __init__(self) -> None:
        self.requests: list[Request] = []
        self.closed: bool = False
        # None answers normally; scripted entries are consumed one per request
        self._scripted: deque[FakeResponse | Exception | None] = deque()

    def fail_next(
        self, status: int, *, times: int = 1, retry_after: str | None = None, after: int = 0
    ) -> None:
        """
        Fail `times` requests with `status`, once `after` more requests have been
        answered normally.
        """
        headers = {"retry-after": retry_after} if retry_after is not None else {}
        for _ in range(after):
            self._scripted.append(None)
        for _ in range(times):
            self._scripted.append(FakeResponse(status, {"detail": "scripted"}, headers))

    def raise_next(self, error: Exception, *, times: int = 1) -> None:
        for _ in range(times):
            self._scripted.append(error)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.ashutdown()

    async def acall(self, request: Request) -> ResponseWrapper:
        self.requests.append(request)

        scripted = self._scripted.popleft() if self._scripted else None
        if isinstance(scripted, Exception):
            raise scripted
        if scripted is not None:
            return scripted

        match request.url:
            case "/api/ping":
                return FakeResponse(200, {"status": "ok"})
            case "/api/price":
                return self._answer(request, self._price_body)
            case "/api/availability":
                return self._answer(request, self._availability_body)
            case _:
                return FakeResponse(404, {"detail": "Not Found"})

    async def ashutdown(self) -> None:
        self.closed = True

    def _answer(
        self, request: Request, build: Callable[[str, date, list[str]], JsonValue]
    ) -> FakeResponse:
        body = cast(dict[str, Any], request.json)
        products: list[str] = body["products"]
        if not 1 <= len(products) <= MAX_PRODUCTS_PER_REQUEST:
            return FakeResponse(422, {"detail": [{"loc": ["body", "products"], "msg": "size"}]})

        return FakeResponse(
            200, build(body["customer"], date.fromisoformat(body["requestedDate"]), products)
        )

    @staticmethod
    def _price_body(customer: str, requested: date, products: list[str]) -> JsonValue:
        return {
            "customerId": customer,
            "currency": "EUR",
            "pricingDate": _timestamp(requested),
            "products": [_SCRIPTED_PRICES[p](p) for p in products if p in _SCRIPTED_PRICES],
        }

    @staticmethod
    def _availability_body(_customer: str, requested: date, products: list[str]) -> JsonValue:
        return {
            "timeNow": _TIME_NOW,
            "requestedDate": _timestamp(requested),
            "products": [
                _SCRIPTED_AVAILABILITY[p](p, requested)
                for p in products
                if p in _SCRIPTED_AVAILABILITY
            ],
        }


async def _no_sleep(_seconds: float) -> None:
    return None


def make_fake_client(
    api: FakeValioAimoApi | None = None,
    *,
    api_key: str = FAKE_API_KEY,
    sleep: Sleep = _no_sleep,
    max_attempts: int = 3,
    backoff_base_seconds: float = 0.5,
) -> ValioAimoClient:
    """
    A real `ValioAimoClient` on top of the fake API. Backoff sleeps are skipped by
    default; pass `sleep` to record them.
    """
    return ValioAimoClient(
        api_url=FAKE_API_URL,
        api_key=api_key,
        transport=api or FakeValioAimoApi(),
        max_attempts=max_attempts,
        backoff_base_seconds=backoff_base_seconds,
        sleep=sleep,
    )
