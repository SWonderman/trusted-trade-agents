import json as _json
from types import TracebackType
from typing import Self, cast, override
from collections.abc import Mapping

from pydantic import BaseModel, JsonValue

from httpkit.dataclasses import Request
from httpkit.response import ResponseWrapper
from httpkit.client import HttpkitBaseAsyncClient, HttpkitBaseSyncClient
from httpkit.transport.base import AsyncTransport, SyncTransport


class Product(BaseModel):
    """A small response model used across client tests."""

    id: int
    name: str


class FakeResponse(ResponseWrapper):
    def __init__(
        self,
        status: int = 200,
        body: str = "",
        headers: Mapping[str, str] | None = None,
    ):
        self._status: int = status
        self._body: str = body
        self._headers: Mapping[str, str] = headers or {}

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
        return cast(JsonValue, _json.loads(self._body))

    @override
    def headers(self) -> dict[str, str]:
        return dict(self._headers)


class FakeTransport:
    def __init__(
        self, response: ResponseWrapper | None = None, raises: Exception | None = None
    ) -> None:
        self._response: ResponseWrapper | None = response
        self._raises: Exception | None = raises

        self.received: Request | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return

    def call(self, request: Request) -> ResponseWrapper:
        self.received = request

        if self._raises:
            raise self._raises

        return self._response or FakeResponse()

    def shutdown(self) -> None:
        return


class FakeAsyncTransport:
    def __init__(
        self, response: ResponseWrapper | None = None, raises: Exception | None = None
    ):
        self._response: ResponseWrapper | None = response
        self._raises: Exception | None = raises

        self.received: Request | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return

    async def acall(self, request: Request) -> ResponseWrapper:
        self.received = request

        if self._raises:
            raise self._raises

        return self._response or FakeResponse()

    async def ashutdown(self) -> None:
        return


class FakeClient(HttpkitBaseSyncClient):
    headers: Mapping[str, str] = {}

    def __init__(self, api_url: str, api_key: str, transport: SyncTransport) -> None:
        super().__init__(api_url=api_url, api_key=api_key, transport=transport)

    @override
    def _get_headers(self, request: Request) -> Mapping[str, str]:
        return self.headers


class FakeAsyncClient(HttpkitBaseAsyncClient):
    headers: Mapping[str, str] = {}

    def __init__(self, api_url: str, api_key: str, transport: AsyncTransport) -> None:
        super().__init__(api_url=api_url, api_key=api_key, transport=transport)

    @override
    def _get_headers(self, request: Request) -> Mapping[str, str]:
        return self.headers
