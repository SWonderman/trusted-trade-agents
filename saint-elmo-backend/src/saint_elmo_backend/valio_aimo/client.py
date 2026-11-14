"""
Thin async client for the Valio Aimo API: price, availability and ping.

It only talks to the API. No caching and no domain rules: those belong to the
offers layer (#12).
"""

import asyncio
import random
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import date
from http import HTTPMethod
from itertools import batched
from typing import overload, override

from pydantic import BaseModel, JsonValue

from saint_elmo_backend.core.settings import Settings
from saint_elmo_backend.httpkit.builders.request_header import RequestHeaderBuilder
from saint_elmo_backend.httpkit.client import HttpkitBaseAsyncClient
from saint_elmo_backend.httpkit.dataclasses import Request, Response
from saint_elmo_backend.httpkit.exceptions import HttpkitError, HttpkitStatusError
from saint_elmo_backend.httpkit.transport.base import AsyncTransport
from saint_elmo_backend.httpkit.transport.httpx.asynchronous import HttpxAsyncTransport
from saint_elmo_backend.httpkit.transport.httpx.config import HttpxClientConfig
from saint_elmo_backend.valio_aimo.exceptions import ValioAimoNotConfigured, ValioAimoUnavailable
from saint_elmo_backend.valio_aimo.schemas import (
    AvailabilityResponse,
    PriceResponse,
    ProductAvailability,
    ProductPrice,
    ProductsRequest,
)

# The API rejects a longer product list with 422
MAX_PRODUCTS_PER_REQUEST = 1000
# A Retry-After longer than this is not waited out: the call fails instead of hanging
MAX_RETRY_AFTER_SECONDS = 10.0
# Backoff delays are spread by ±20% so concurrent callers don't retry in lockstep
_JITTER = 0.2

type Sleep = Callable[[float], Awaitable[None]]


class ValioAimoClient(HttpkitBaseAsyncClient):
    """
    Without an API URL or key the client still constructs, so the app starts, but every
    call raises `ValioAimoNotConfigured`.

    Retries 429, 5xx, timeouts and connection errors up to `max_attempts` in total, with
    exponential backoff from `backoff_base_seconds` (or the server's `Retry-After`).
    Anything else fails straight away. Every failure surfaces as `ValioAimoUnavailable`.
    """

    def __init__(
        self,
        api_url: str | None,
        api_key: str | None,
        transport: AsyncTransport,
        *,
        max_attempts: int = 3,
        backoff_base_seconds: float = 0.5,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        super().__init__(api_url=api_url or "", api_key=api_key or "", transport=transport)

        self._configured: bool = bool(api_url and api_key)
        self._max_attempts: int = max(1, max_attempts)
        self._backoff_base_seconds: float = backoff_base_seconds
        self._sleep: Sleep = sleep

    @override
    def _get_headers(self, request: Request) -> Mapping[str, str]:
        return (
            RequestHeaderBuilder().add_accept().add_custom_field("X-API-Key", self._api_key).build()
        )

    async def aclose(self) -> None:
        await self._transport.ashutdown()

    async def price(
        self, customer: str, requested_date: date, products: Sequence[str]
    ) -> dict[str, ProductPrice]:
        """
        `POST /api/price`. Maps product code to its price, values as the API sent them.
        A product the API leaves out is absent.
        """
        responses = await self._post_products(
            "/api/price", customer, requested_date, products, PriceResponse
        )
        return {item.product_id: item for r in responses for item in r.products}

    async def availability(
        self, customer: str, requested_date: date, products: Sequence[str]
    ) -> dict[str, ProductAvailability]:
        """
        `POST /api/availability`. Maps product code to its availability, values as the
        API sent them. A product the API leaves out is absent.
        """
        responses = await self._post_products(
            "/api/availability", customer, requested_date, products, AvailabilityResponse
        )
        return {item.product_id: item for r in responses for item in r.products}

    async def ping(self) -> JsonValue | None:
        """
        `GET /api/ping`, to check the base URL and the key.
        """
        self._ensure_configured()

        response = await self._send("/api/ping", method=HTTPMethod.GET)
        return response.payload

    async def _post_products[T: BaseModel](
        self,
        url: str,
        customer: str,
        requested_date: date,
        products: Sequence[str],
        response_model: type[T],
    ) -> list[T]:
        self._ensure_configured()

        results: list[T] = []
        # One after another, not concurrently: the API's rate limits are unpublished.
        # Duplicates are dropped so they don't cost a slot in a batch.
        for batch in batched(dict.fromkeys(products), MAX_PRODUCTS_PER_REQUEST, strict=False):
            body = ProductsRequest(
                customer=customer,
                requested_date=requested_date.isoformat(),
                products=list(batch),
            )
            response = await self._send(
                url,
                method=HTTPMethod.POST,
                json=body.model_dump(by_alias=True),
                response_model=response_model,
            )
            results.append(response.require_payload())
        return results

    @overload
    async def _send[T: BaseModel](
        self,
        url: str,
        *,
        method: HTTPMethod,
        json: JsonValue | None = None,
        response_model: type[T],
    ) -> Response[T]: ...
    @overload
    async def _send(
        self,
        url: str,
        *,
        method: HTTPMethod,
        json: JsonValue | None = None,
        response_model: None = None,
    ) -> Response[JsonValue | None]: ...

    async def _send[T: BaseModel](
        self,
        url: str,
        *,
        method: HTTPMethod,
        json: JsonValue | None = None,
        response_model: type[T] | None = None,
    ) -> Response[T] | Response[JsonValue | None]:
        """
        One request with retries. Raises `ValioAimoUnavailable` once it gives up.
        """
        attempt = 1
        while True:
            try:
                if response_model is None:
                    return await self.arequest(url, method=method, json=json)
                return await self.arequest(
                    url, method=method, json=json, response_model=response_model
                )
            except HttpkitError as e:
                status_code = e.status_code if isinstance(e, HttpkitStatusError) else None
                delay = self._retry_delay(e, attempt)
                if delay is None:
                    raise ValioAimoUnavailable(
                        f"Valio Aimo API {method} {url} failed after {attempt} attempt(s): {e}",
                        status_code=status_code,
                        attempts=attempt,
                    ) from e

            await self._sleep(delay)
            attempt += 1

    def _retry_delay(self, error: HttpkitError, attempt: int) -> float | None:
        """
        Seconds to wait before the next attempt, or None to give up.
        """
        if attempt >= self._max_attempts:
            return None

        backoff = self._backoff_base_seconds * 2 ** (attempt - 1)
        backoff *= random.uniform(1 - _JITTER, 1 + _JITTER)

        if not isinstance(error, HttpkitStatusError):
            # Timeouts and connection errors are retryable; other transport and
            # validation errors are not
            return backoff if error.is_retryable() else None

        # 429 and every 5xx; other 4xx (401 wrong key, 422) fail straight away
        if error.status_code != 429 and not 500 <= error.status_code <= 599:
            return None

        retry_after = _retry_after_seconds(error.headers)
        if retry_after is None:
            return backoff
        if retry_after > MAX_RETRY_AFTER_SECONDS:
            return None
        return max(retry_after, backoff)

    def _ensure_configured(self) -> None:
        if not self._configured:
            raise ValioAimoNotConfigured()


def create_valio_aimo_client(settings: Settings) -> ValioAimoClient:
    """
    The app's client, on one shared `httpx.AsyncClient`. Close it with `aclose()`.
    """
    api_key = settings.valio_aimo_api_key
    return ValioAimoClient(
        api_url=settings.valio_aimo_api_url,
        api_key=api_key.get_secret_value() if api_key else None,
        transport=HttpxAsyncTransport(
            HttpxClientConfig(base_url=settings.valio_aimo_api_url or "")
        ),
        max_attempts=settings.valio_aimo_max_attempts,
        backoff_base_seconds=settings.valio_aimo_backoff_base_seconds,
    )


def _retry_after_seconds(headers: Mapping[str, str]) -> float | None:
    """
    `Retry-After` in seconds, when given as a number. The HTTP-date form is ignored and
    the regular backoff applies.
    """
    value = next((v for k, v in headers.items() if k.lower() == "retry-after"), None)
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None
