"""
`GET /api/v1/agents/me/mandate`, exercised over HTTP: an agent reads its own mandate.
"""

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import delete

from saint_elmo_backend.accounts.tests.factories import (
    make_organization,
    make_user,
    user_session_headers,
)
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.agents.tests.factories import bearer, issue_token, make_agent
from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.enums import AllergenStrictness
from saint_elmo_backend.catalog.models import Category
from saint_elmo_backend.mandates.dtos import CategorySpendCap
from saint_elmo_backend.mandates.enums import SpendPeriod, SubstitutionPolicy
from saint_elmo_backend.mandates.models import Mandate
from saint_elmo_backend.mandates.services import write_mandate
from saint_elmo_backend.mandates.tests.factories import make_terms

MANDATE_URL = "/api/v1/agents/me/mandate"


async def test_agent_reads_its_own_mandate_and_never_another(reference_data, session, client):
    hotel = await make_organization(session, name="Hotel chain")
    hospital = await make_organization(session, name="Hospital kitchen")
    # Category codes are checked against the catalogue when a mandate is written
    session.add(Category(code="10400"))
    dairy = await make_agent(
        session,
        hotel,
        name="dairy-restock",
        mandate=replace(
            make_terms(),
            max_order_total=Decimal("2000"),
            period_spend_cap=Decimal("5000"),
            spend_period=SpendPeriod.WEEK,
            required_claims=(ClaimCode(type="FREE_FROM", element="LACTOSE"),),
            category_spend_caps=(CategorySpendCap(category_code="10400", cap=Decimal("800")),),
            auto_approve_up_to=Decimal("1500"),
            substitution_policy=SubstitutionPolicy.IF_REQUIREMENTS_HOLD,
        ),
    )
    ward = await make_agent(
        session,
        hospital,
        name="ward-kitchen",
        mandate=replace(
            make_terms(),
            excluded_allergens=("AM", "AW"),
            allergen_strictness=AllergenStrictness.DECLARED_FREE,
            substitution_policy=SubstitutionPolicy.ALWAYS_NEEDS_APPROVAL,
        ),
    )
    dairy_token = await issue_token(session, dairy, scopes=[Scope.MANDATE_READ])
    ward_token = await issue_token(session, ward, scopes=[Scope.MANDATE_READ])
    await session.commit()

    dairy_mandate = (await client.get(MANDATE_URL, headers=bearer(dairy_token))).json()
    ward_mandate = (await client.get(MANDATE_URL, headers=bearer(ward_token))).json()

    assert dairy_mandate["agent"] == {"id": str(dairy.public_id), "name": "dairy-restock"}
    assert dairy_mandate["buyerOrganisation"] == {"name": "Hotel chain"}
    assert dairy_mandate["maxOrderTotal"] == 2000
    assert dairy_mandate["periodSpendCap"] == 5000
    assert dairy_mandate["spendPeriod"] == "WEEK"
    assert dairy_mandate["requiredClaims"] == [{"type": "FREE_FROM", "element": "LACTOSE"}]
    assert dairy_mandate["categorySpendCaps"] == [{"categoryCode": "10400", "cap": 800}]
    assert dairy_mandate["autoApproveUpTo"] == 1500
    assert dairy_mandate["substitutionPolicy"] == "IF_REQUIREMENTS_HOLD"
    assert dairy_mandate["excludedAllergens"] == []
    assert dairy_mandate["version"] == 1

    assert ward_mandate["agent"] == {"id": str(ward.public_id), "name": "ward-kitchen"}
    assert ward_mandate["buyerOrganisation"] == {"name": "Hospital kitchen"}
    assert ward_mandate["excludedAllergens"] == ["AM", "AW"]
    assert ward_mandate["allergenStrictness"] == "declared_free"
    assert ward_mandate["substitutionPolicy"] == "ALWAYS_NEEDS_APPROVAL"
    assert ward_mandate["requiredClaims"] == []


async def test_mandate_edit_applies_to_a_live_token_on_its_next_request(
    reference_data, session, client
):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent, scopes=[Scope.MANDATE_READ])
    await session.commit()
    assert (await client.get(MANDATE_URL, headers=bearer(token))).json()["version"] == 1

    await write_mandate(session, agent, replace(make_terms(), max_order_total=Decimal("750")))
    await session.commit()

    mandate = (await client.get(MANDATE_URL, headers=bearer(token))).json()
    assert mandate["maxOrderTotal"] == 750
    assert mandate["version"] == 2


async def test_token_without_mandate_read_is_forbidden(clean_db, session, client):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent, scopes=[Scope.CATALOG_READ])
    await session.commit()

    response = await client.get(MANDATE_URL, headers=bearer(token))

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


async def test_user_session_is_forbidden(clean_db, session, client):
    user = await make_user(session, await make_organization(session))
    await session.commit()

    response = await client.get(MANDATE_URL, headers=user_session_headers(user))

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


async def test_no_credential_is_unauthorized(clean_db, client):
    response = await client.get(MANDATE_URL)

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.parametrize("period", list(SpendPeriod))
async def test_period_spend_covers_the_current_period_and_is_zero_without_orders(
    clean_db, session, client, period
):
    agent = await make_agent(
        session,
        await make_organization(session),
        mandate=replace(make_terms(), period_spend_cap=Decimal("5000"), spend_period=period),
    )
    token = await issue_token(session, agent, scopes=[Scope.MANDATE_READ])
    await session.commit()

    before = datetime.now(UTC)
    period_spend = (await client.get(MANDATE_URL, headers=bearer(token))).json()["periodSpend"]

    start = datetime.fromisoformat(period_spend["periodStart"])
    end = datetime.fromisoformat(period_spend["periodEnd"])
    assert start <= before < end
    local_start = start.astimezone(ZoneInfo("Europe/Helsinki"))
    assert local_start.time() == time(0, 0)
    if period is SpendPeriod.WEEK:
        assert local_start.weekday() == 0
        assert end - start <= timedelta(days=7, hours=1)
    else:
        assert local_start.day == 1
        assert end.astimezone(ZoneInfo("Europe/Helsinki")).day == 1
    assert period_spend["committed"] == 0
    assert period_spend["remaining"] == 5000


async def test_response_model_is_in_openapi(client):
    schema = (await client.get("/openapi.json")).json()

    operation = schema["paths"][MANDATE_URL]["get"]
    assert operation["security"] == [{"AgentToken": ["mandate:read"]}]
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response == {"$ref": "#/components/schemas/MandateResponse"}
    properties = schema["components"]["schemas"]["MandateResponse"]["properties"]
    assert {
        "version",
        "agent",
        "buyerOrganisation",
        "maxOrderTotal",
        "periodSpendCap",
        "spendPeriod",
        "categorySpendCaps",
        "allowedCategoryCodes",
        "blockedCategoryCodes",
        "allowedVendors",
        "blockedVendors",
        "allowedCountriesOfOrigin",
        "requiredClaims",
        "requiredLabels",
        "requiredDiets",
        "excludedAllergens",
        "allergenStrictness",
        "substitutionPolicy",
        "maxSubstitutePriceIncreasePct",
        "laterDeliveryNeedsApproval",
        "minDeliveryReliability",
        "autoApproveUpTo",
        "periodSpend",
    } <= properties.keys()


async def test_agent_without_a_mandate_gets_mandate_not_found(clean_db, session, client):
    agent = await make_agent(session, await make_organization(session))
    token = await issue_token(session, agent, scopes=[Scope.MANDATE_READ])
    # Every agent is given a mandate; this one lost it after its token was issued
    await session.execute(delete(Mandate).where(Mandate.agent_id == agent.id))
    await session.commit()

    response = await client.get(MANDATE_URL, headers=bearer(token))

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "MANDATE_NOT_FOUND"
