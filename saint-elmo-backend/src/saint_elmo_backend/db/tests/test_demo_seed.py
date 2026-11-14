"""
The demo seed: two buyer organisations, their buyer admins and agents with mandates,
and no Agent tokens.
"""

from decimal import Decimal

from sqlalchemy import func, select

from saint_elmo_backend.accounts import services as account_services
from saint_elmo_backend.accounts.enums import Role
from saint_elmo_backend.accounts.models import Organization
from saint_elmo_backend.agents.models import Agent, AgentCredential
from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.enums import AllergenStrictness
from saint_elmo_backend.catalog.models import Category
from saint_elmo_backend.db.seeders import demo
from saint_elmo_backend.mandates import services as mandate_services
from saint_elmo_backend.mandates.enums import SpendPeriod, SubstitutionPolicy


async def _seed(session) -> None:
    # The catalogue seeder normally provides the categories the hotel mandate names
    session.add_all(Category(code=code) for code in demo.DAIRY_CATEGORY_CODES)
    await demo.seed_demo(session)
    await session.commit()


async def _mandate(session, agent_name: str):
    agent = await session.scalar(select(Agent).where(Agent.name == agent_name))
    return agent, await mandate_services.get_agent_mandate(
        session, organization_id=agent.org_id, agent_id=agent.id
    )


async def test_hotel_chain_with_dairy_restock(reference_data, session):
    await _seed(session)

    agent, mandate = await _mandate(session, "dairy-restock")
    terms = mandate.terms

    organization = await session.get(Organization, agent.org_id)
    assert organization.name == demo.HOTEL_CHAIN
    assert terms.allowed_category_codes == demo.DAIRY_CATEGORY_CODES
    assert terms.required_claims == (ClaimCode(type="FREE_FROM", element="LACTOSE"),)
    assert terms.auto_approve_up_to == Decimal("1500")
    assert terms.max_order_total == Decimal("2000")
    assert terms.period_spend_cap == Decimal("5000")
    assert terms.spend_period is SpendPeriod.WEEK
    assert terms.substitution_policy is SubstitutionPolicy.IF_REQUIREMENTS_HOLD


async def test_hospital_kitchen_with_ward_kitchen(reference_data, session):
    await _seed(session)

    agent, mandate = await _mandate(session, "ward-kitchen")
    terms = mandate.terms

    organization = await session.get(Organization, agent.org_id)
    assert organization.name == demo.HOSPITAL_KITCHEN
    assert terms.excluded_allergens == ("AM", "AW")
    assert terms.allergen_strictness is AllergenStrictness.DECLARED_FREE
    assert terms.substitution_policy is SubstitutionPolicy.ALWAYS_NEEDS_APPROVAL
    # Unset unless a buyer admin opts in
    assert terms.min_delivery_reliability is None


async def test_each_buyer_organisation_has_a_buyer_admin_who_can_log_in(reference_data, session):
    await _seed(session)

    names = set()
    for email in (demo.HOTEL_BUYER_ADMIN_EMAIL, demo.HOSPITAL_BUYER_ADMIN_EMAIL):
        user = await account_services.authenticate_user(session, email, demo.DEMO_PASSWORD)
        assert user.role is Role.BUYER_ADMIN
        names.add(user.organization.name)

    assert names == {demo.HOTEL_CHAIN, demo.HOSPITAL_KITCHEN}


async def test_no_agent_token_is_seeded(reference_data, session):
    await _seed(session)

    assert await session.scalar(select(func.count()).select_from(AgentCredential)) == 0


async def test_seeding_twice_changes_nothing(reference_data, session):
    await _seed(session)
    await demo.seed_demo(session)
    await session.commit()

    assert await session.scalar(select(func.count()).select_from(Organization)) == 2
    assert await session.scalar(select(func.count()).select_from(Agent)) == 2
