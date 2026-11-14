from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import replace
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
from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.enums import AllergenContainment
from saint_elmo_backend.catalog.tests.factories import make_product
from saint_elmo_backend.mandates.dtos import MandateTerms
from saint_elmo_backend.mandates.tests.factories import make_terms
from saint_elmo_backend.offers.cache import OfferCache
from saint_elmo_backend.valio_aimo.testing import (
    EILA_10L,
    LATE_PRODUCT,
    PRICE_ERROR_PRODUCT,
    RESTOCKED_PRODUCT,
    FakeValioAimoApi,
    make_fake_client,
)

DAIRY = "10400"

# Like the demo's dairy-restock mandate: dairy only, lactose free, auto-approves up to 1,500 €
DAIRY_RESTOCK = replace(
    make_terms(),
    max_order_total=Decimal("2000"),
    auto_approve_up_to=Decimal("1500"),
    allowed_category_codes=(DAIRY,),
    required_claims=(ClaimCode(type="FREE_FROM", element="LACTOSE"),),
)

type Authenticate = Callable[..., Awaitable[None]]


@pytest.fixture
def fake_api() -> FakeValioAimoApi:
    return FakeValioAimoApi()


@pytest.fixture
async def organization(session: AsyncSession) -> Organization:
    return await make_organization(session)


@pytest.fixture
async def quoted_products(reference_data, session: AsyncSession) -> None:
    """
    Lactose-free dairy rows for the fake API's milk and its stock scenarios.
    """
    lactose_free = {
        "category": DAIRY,
        "claims": [("FREE_FROM", "LACTOSE")],
        "allergens": {"AM": AllergenContainment.FREE_FROM, "AW": AllergenContainment.FREE_FROM},
    }
    await make_product(
        session,
        code=EILA_10L,
        names={"en": "Valio Eila® semi skimmed milk drink 10 l novobox lactose free"},
        sales_unit="KI",
        base_unit="ST",
        allowed_lot_size=Decimal("1"),
        units={"ST": Decimal("1"), "KI": Decimal("2")},
        deposits=["DEP-NOVOBOX"],
        **lactose_free,
    )
    for code, name in [
        (LATE_PRODUCT, "Late quark 2 kg"),
        (RESTOCKED_PRODUCT, "Restocked quark 2 kg"),
        (PRICE_ERROR_PRODUCT, "Unpriced yoghurt 2 kg"),
    ]:
        await make_product(
            session,
            code=code,
            names={"en": name},
            sales_unit="KI",
            base_unit="KI",
            allowed_lot_size=Decimal("1"),
            **lactose_free,
        )
    await session.commit()


@pytest.fixture
async def authenticate(
    client: AsyncClient, session: AsyncSession, organization: Organization
) -> Authenticate:
    """
    Authenticates `client` as a new agent with `mandate`, in `organization` unless
    another is given.
    """

    async def _authenticate(
        mandate: MandateTerms = DAIRY_RESTOCK,
        *,
        organization: Organization = organization,
        scopes: tuple[Scope, ...] = (Scope.QUOTE_CREATE,),
    ) -> None:
        agent = await make_agent(session, organization, mandate=mandate)
        token = await issue_token(session, agent, scopes=scopes)
        await session.commit()
        client.headers.update(bearer(token))

    return _authenticate


@pytest.fixture
async def client(
    app: FastAPI, client: AsyncClient, quoted_products, fake_api: FakeValioAimoApi
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
