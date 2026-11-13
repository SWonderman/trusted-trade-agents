from typing import Protocol

import pytest

from collections.abc import Mapping

from saint_elmo_backend.httpkit.response import ResponseWrapper
from saint_elmo_backend.httpkit.tests.fakes import (
    FakeAsyncClient,
    FakeAsyncTransport,
    FakeClient,
    FakeTransport,
)


class MakeClient(Protocol):
    def __call__(
        self,
        response: ResponseWrapper | None = None,
        raises: Exception | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[FakeClient, FakeTransport]: ...


class MakeAsyncClient(Protocol):
    def __call__(
        self,
        response: ResponseWrapper | None = None,
        raises: Exception | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[FakeAsyncClient, FakeAsyncTransport]: ...


@pytest.fixture
def make_client() -> MakeClient:
    def _make(
        response: ResponseWrapper | None = None,
        raises: Exception | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[FakeClient, FakeTransport]:
        transport = FakeTransport(response=response, raises=raises)
        client = FakeClient(api_url="https://api", api_key="key", transport=transport)
        if headers is not None:
            client.headers = headers

        return client, transport

    return _make


@pytest.fixture
def make_async_client() -> MakeAsyncClient:
    def _make(
        response: ResponseWrapper | None = None,
        raises: Exception | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> tuple[FakeAsyncClient, FakeAsyncTransport]:
        transport = FakeAsyncTransport(response=response, raises=raises)
        client = FakeAsyncClient(
            api_url="https://api", api_key="key", transport=transport
        )
        if headers is not None:
            client.headers = headers

        return client, transport

    return _make
