"""Test harness: the real MCP server over streamable HTTP, with the backend faked.

The MCP app runs in-process behind an ASGI transport, so tests go through the
same HTTP path as a real client, headers included. The backend is an
`httpx.MockTransport` whose handler each test sets.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

import httpx
import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from saint_elmo_mcp.backend import BackendClient
from saint_elmo_mcp.schemas import SHORTFALL_CODES
from saint_elmo_mcp.server import build_server

# Host must carry a port: the SDK's DNS-rebinding protection rejects bare "localhost"
MCP_URL = "http://localhost:8001/mcp"


class FakeBackend:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.handler: Callable[[httpx.Request], httpx.Response] = lambda _: httpx.Response(
            500, text="no handler set"
        )

    def respond_json(self, status: int, body: Any) -> None:
        self.handler = lambda _: httpx.Response(status, json=body)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.handler(request)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self._handle)


@pytest.fixture
def backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def connect(backend: FakeBackend):
    """`async with connect(headers) as client:` gives an MCP client session."""

    @asynccontextmanager
    async def _connect(
        headers: dict[str, str] | None = None,
        backend_transport: httpx.AsyncBaseTransport | None = None,
    ) -> AsyncIterator[Client]:
        server = build_server(
            BackendClient(
                "http://backend.test", transport=backend_transport or backend.transport
            )
        )
        app = server.streamable_http_app(stateless_http=True, json_response=True)
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app), headers=headers or {}
            ) as http:
                async with Client(streamable_http_client(MCP_URL, http_client=http)) as client:
                    yield client

    return _connect


def error(code: str, message: str) -> dict:
    """A backend error envelope."""
    return {"error": {"code": code, "message": message, "requestId": "r-1"}}


def text(result) -> str:
    return "\n".join(block.text for block in result.content if block.type == "text")


async def tool_named(client: Client, name: str):
    return next(t for t in (await client.list_tools()).tools if t.name == name)


def assert_sends_shortfalls_to_find_substitutes(description: str | None) -> None:
    """A quote or order line can first fall short there, since live availability is re-checked."""
    assert description is not None
    prose = " ".join(description.split())
    assert "find_substitutes" in prose
    for code in SHORTFALL_CODES:
        assert code in prose, code
    assert "`substitutesFor` set to the original code" in prose


def search_response(*items: dict[str, Any], total: int | None = None) -> dict[str, Any]:
    return {
        "total": len(items) if total is None else total,
        "items": list(items),
        "provenance": {
            "source": "Valio Aimo static catalog + GS1 Synkka",
            "catalogSnapshotDate": "2026-11-01",
        },
    }


MILK_HIT = {
    "code": "463038",
    "name": "Valio Eila semi skimmed milk drink 10 l novobox lactose free",
    "gtin": "6408430000001",
    "categoryCode": "101010",
    "vendor": "Valio",
    "brand": "Valio Eila",
    "salesUnit": "KI",
    "baseUnit": "ST",
    "allowedLotSize": 0.01,
    "units": [{"code": "KI", "sizeInBaseUnits": 2}, {"code": "ST", "sizeInBaseUnits": 1}],
    "variableUnit": False,
    "hasDeposit": False,
    "claims": [{"type": "FREE_FROM", "element": "LACTOSE"}],
    "diets": [],
    "labels": [],
    "countryOfOrigin": "fi",
    "deliveryReliability": None,
    "carbonFootprint": {"value": 1.2, "basis": "PRODUCT_GROUP_AVERAGE"},
    "relevance": 0.87,
    "allergens": [{"code": "AM", "status": "CONTAINS"}],
    "somethingTheAgentDoesNotNeed": "ignored",
}
