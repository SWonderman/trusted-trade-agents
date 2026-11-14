from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts.models import Organization
from saint_elmo_backend.accounts.tests.factories import make_organization
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.agents.tests.factories import bearer, issue_token, make_agent
from saint_elmo_backend.api.dependencies import get_offer_cache, get_valio_aimo_client
from saint_elmo_backend.catalog.tests.factories import make_product
from saint_elmo_backend.offers.cache import OfferCache
from saint_elmo_backend.valio_aimo.testing import (
    BLOCKED_PRODUCT,
    EILA_10L,
    LATE_PRODUCT,
    PRICE_ERROR_PRODUCT,
    TERMINAL_PRODUCT,
    UNDELIVERABLE_PRODUCT,
    FakeValioAimoApi,
    make_fake_client,
)


@pytest.fixture
def fake_api() -> FakeValioAimoApi:
    return FakeValioAimoApi()


@pytest.fixture
def offer_cache() -> OfferCache:
    return OfferCache()


@pytest.fixture
async def organization(session: AsyncSession) -> Organization:
    return await make_organization(session)


@pytest.fixture
async def client(
    app: FastAPI,
    client: AsyncClient,
    session: AsyncSession,
    organization: Organization,
    fake_api: FakeValioAimoApi,
    offer_cache: OfferCache,
) -> AsyncIterator[AsyncClient]:
    """
    The root `client` on the fake Valio Aimo API with a fresh offer cache, authenticated
    as an agent holding only `offers:read`.
    """
    agent = await make_agent(session, organization)
    token = await issue_token(session, agent, scopes=[Scope.OFFERS_READ])
    await session.commit()

    fake_client = make_fake_client(fake_api)
    app.dependency_overrides[get_valio_aimo_client] = lambda: fake_client
    app.dependency_overrides[get_offer_cache] = lambda: offer_cache
    client.headers.update(bearer(token))
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_valio_aimo_client, None)
        app.dependency_overrides.pop(get_offer_cache, None)


@pytest.fixture
async def scripted_products(reference_data, session: AsyncSession) -> None:
    """
    Catalogue rows for every product the fake Valio Aimo API scripts.
    """
    await make_product(
        session,
        code=EILA_10L,
        names={"en": "Valio Eila® semi skimmed milk drink 10 l novobox lactose free"},
        sales_unit="KI",
        base_unit="ST",
        allowed_lot_size=Decimal("1"),
        units={"ST": Decimal("1"), "KI": Decimal("2")},
        delivery_reliability=Decimal("0.982"),
        carbon_footprint=Decimal("1.100"),
    )
    for code, name in [
        (TERMINAL_PRODUCT, "Terminal cheese 5 kg"),
        (PRICE_ERROR_PRODUCT, "Unpriced yoghurt 2 kg"),
        (UNDELIVERABLE_PRODUCT, "Undeliverable butter 2 kg"),
        (LATE_PRODUCT, "Late quark 2 kg"),
        (BLOCKED_PRODUCT, "Blocked cream 500 g"),
    ]:
        await make_product(
            session,
            code=code,
            names={"en": name},
            sales_unit="KI" if code != BLOCKED_PRODUCT else "ST",
            base_unit="KI" if code != BLOCKED_PRODUCT else "ST",
            allowed_lot_size=Decimal("1"),
        )
    await session.commit()
