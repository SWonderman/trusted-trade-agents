from collections.abc import AsyncIterator, Awaitable, Callable
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
from saint_elmo_backend.catalog.enums import AllergenContainment
from saint_elmo_backend.catalog.tests.factories import make_product
from saint_elmo_backend.mandates.dtos import MandateTerms
from saint_elmo_backend.offers.cache import OfferCache
from saint_elmo_backend.quotes.tests.conftest import DAIRY, DAIRY_RESTOCK
from saint_elmo_backend.valio_aimo.testing import EILA_10L, FakeValioAimoApi, make_fake_client

type Authenticate = Callable[..., Awaitable[None]]

# Lactose free, and declared free from milk and gluten
LACTOSE_FREE = {
    "category": DAIRY,
    "claims": [("FREE_FROM", "LACTOSE")],
    "allergens": {"AM": AllergenContainment.FREE_FROM, "AW": AllergenContainment.FREE_FROM},
}


@pytest.fixture
def fake_api() -> FakeValioAimoApi:
    return FakeValioAimoApi()


@pytest.fixture
async def organization(session: AsyncSession) -> Organization:
    return await make_organization(session)


@pytest.fixture
async def original(reference_data, session: AsyncSession) -> None:
    """
    The fake API's Eila 10 l milk, 20 L per KI at 1.57 €/L: the product to substitute.
    """
    await make_product(
        session,
        code=EILA_10L,
        names={"en": "Valio Eila® semi skimmed milk drink 10 l novobox lactose free"},
        sales_unit="KI",
        base_unit="ST",
        allowed_lot_size=Decimal("1"),
        units={"ST": Decimal("1"), "KI": Decimal("2")},
        delivery_reliability=Decimal("0.950"),
        carbon_footprint=Decimal("1.200"),
        **LACTOSE_FREE,
    )
    await session.commit()


@pytest.fixture
async def authenticate(
    client: AsyncClient, session: AsyncSession, organization: Organization
) -> Authenticate:
    """
    Authenticates `client` as a new agent of `organization` with `mandate`.
    """

    async def _authenticate(
        mandate: MandateTerms = DAIRY_RESTOCK,
        *,
        scopes: tuple[Scope, ...] = (Scope.OFFERS_READ,),
    ) -> None:
        agent = await make_agent(session, organization, mandate=mandate)
        token = await issue_token(session, agent, scopes=scopes)
        await session.commit()
        client.headers.update(bearer(token))

    return _authenticate


@pytest.fixture
async def client(
    app: FastAPI, client: AsyncClient, original, fake_api: FakeValioAimoApi
) -> AsyncIterator[AsyncClient]:
    """
    The root `client` on the fake Valio Aimo API with a fresh offer cache, not yet
    authenticated: see `authenticate`.
    """
    fake_client = make_fake_client(fake_api)
    offer_cache = OfferCache()
    app.dependency_overrides[get_valio_aimo_client] = lambda: fake_client
    app.dependency_overrides[get_offer_cache] = lambda: offer_cache
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_valio_aimo_client, None)
        app.dependency_overrides.pop(get_offer_cache, None)
