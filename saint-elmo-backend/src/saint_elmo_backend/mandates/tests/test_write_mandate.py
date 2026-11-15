"""
Writing a mandate: every code it names is checked against the catalogue's vocabulary,
and every edit bumps its version.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from saint_elmo_backend.accounts.tests.factories import make_organization
from saint_elmo_backend.agents.tests.factories import make_agent
from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.exceptions import UnknownCodesError
from saint_elmo_backend.catalog.models import Category
from saint_elmo_backend.mandates import services
from saint_elmo_backend.mandates.dtos import CategorySpendCap
from saint_elmo_backend.mandates.tests.factories import make_terms


async def test_known_codes_are_accepted(reference_data, session):
    session.add(Category(code="10400"))
    agent = await make_agent(session, await make_organization(session))

    terms = replace(
        make_terms(),
        allowed_category_codes=("10400",),
        category_spend_caps=(CategorySpendCap(category_code="10400", cap=Decimal("100")),),
        required_claims=(ClaimCode(type="FREE_FROM", element="LACTOSE"),),
        required_labels=("EU_ORGANIC_FARMING",),
        required_diets=("VEGAN",),
        excluded_allergens=("AM", "AW"),
    )
    await services.write_mandate(session, agent, terms)

    mandate = await services.get_agent_mandate(
        session, organization_id=agent.org_id, agent_id=agent.id
    )
    assert mandate.terms == terms


async def test_unknown_codes_are_rejected_all_at_once(reference_data, session):
    session.add(Category(code="10400"))
    agent = await make_agent(session, await make_organization(session))

    with pytest.raises(UnknownCodesError) as raised:
        await services.write_mandate(
            session,
            agent,
            replace(
                make_terms(),
                allowed_category_codes=("10400", "NOPE1"),
                blocked_category_codes=("NOPE2",),
                category_spend_caps=(CategorySpendCap(category_code="NOPE3", cap=Decimal("1")),),
                required_claims=(ClaimCode(type="FREE_FROM", element="UNICORN"),),
                required_labels=("SHINY",),
                required_diets=("CARNIVORE",),
                excluded_allergens=("AM", "XX"),
            ),
        )

    assert raised.value.unknown == {
        "allowed_category_codes": ["NOPE1"],
        "blocked_category_codes": ["NOPE2"],
        "category_spend_caps": ["NOPE3"],
        "required_claims": ["UNICORN"],
        "required_labels": ["SHINY"],
        "required_diets": ["CARNIVORE"],
        "excluded_allergens": ["XX"],
    }


async def test_a_rejected_write_leaves_the_mandate_unchanged(reference_data, session):
    agent = await make_agent(session, await make_organization(session))

    with pytest.raises(UnknownCodesError):
        await services.write_mandate(
            session, agent, replace(make_terms(), required_diets=("CARNIVORE",))
        )

    mandate = await services.get_agent_mandate(
        session, organization_id=agent.org_id, agent_id=agent.id
    )
    assert mandate.terms == make_terms()
    assert mandate.version == 1


async def test_every_edit_bumps_the_version(reference_data, session):
    agent = await make_agent(session, await make_organization(session))

    await services.write_mandate(
        session, agent, replace(make_terms(), max_order_total=Decimal("1200"))
    )
    await services.write_mandate(
        session, agent, replace(make_terms(), max_order_total=Decimal("1300"))
    )

    mandate = await services.get_agent_mandate(
        session, organization_id=agent.org_id, agent_id=agent.id
    )
    assert mandate.version == 3
    assert mandate.terms.max_order_total == Decimal("1300")


async def test_writing_the_same_terms_again_is_not_an_edit(reference_data, session):
    agent = await make_agent(session, await make_organization(session))

    await services.write_mandate(session, agent, make_terms())

    mandate = await services.get_agent_mandate(
        session, organization_id=agent.org_id, agent_id=agent.id
    )
    assert mandate.version == 1
