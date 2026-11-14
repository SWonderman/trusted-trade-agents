"""
The app creates one Valio Aimo client in `lifespan`, closes it on shutdown, and hands
it to routes through a dependency that tests override with the shared fake.
"""

from datetime import date

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from saint_elmo_backend.api.annotations import AValioAimoClient
from saint_elmo_backend.api.dependencies import get_valio_aimo_client
from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.main import lifespan
from saint_elmo_backend.valio_aimo.client import ValioAimoClient
from saint_elmo_backend.valio_aimo.exceptions import ValioAimoNotConfigured
from saint_elmo_backend.valio_aimo.testing import EILA_10L, FakeValioAimoApi, make_fake_client


async def test_startup_succeeds_without_configuration_and_calls_say_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unconfigured = get_settings().model_copy(
        update={"valio_aimo_api_url": None, "valio_aimo_api_key": None}
    )
    monkeypatch.setattr("saint_elmo_backend.main.get_settings", lambda: unconfigured)
    app = FastAPI()

    async with lifespan(app):
        client = app.state.valio_aimo_client
        assert isinstance(client, ValioAimoClient)
        with pytest.raises(ValioAimoNotConfigured):
            await client.ping()


async def test_lifespan_closes_the_client_on_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    api = FakeValioAimoApi()
    monkeypatch.setattr(
        "saint_elmo_backend.main.create_valio_aimo_client", lambda _settings: make_fake_client(api)
    )
    app = FastAPI()

    async with lifespan(app):
        assert api.closed is False

    assert api.closed is True


async def test_routes_get_the_client_through_an_overridable_dependency() -> None:
    app = FastAPI()

    @app.get("/eila-price")
    async def eila_price(valio_aimo: AValioAimoClient) -> dict[str, str]:
        prices = await valio_aimo.price(
            customer="123", requested_date=date(2026, 11, 16), products=[EILA_10L]
        )
        price = prices[EILA_10L].catalog_price
        return {"value": str(price.value if price else None)}

    fake = make_fake_client()
    app.dependency_overrides[get_valio_aimo_client] = lambda: fake

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        response = await http.get("/eila-price")

    assert response.status_code == 200
    assert response.json() == {"value": "39.8"}
