"""
`just issue-agent-token`: an Agent token for a seeded agent, issued from the command
line through the same issuance service as the API.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select

from saint_elmo_backend.accounts.models import User
from saint_elmo_backend.agents import command
from saint_elmo_backend.agents.enums import ScopePreset
from saint_elmo_backend.agents.models import AgentCredential
from saint_elmo_backend.agents.tests.factories import bearer
from saint_elmo_backend.catalog.models import Category
from saint_elmo_backend.db.seeders import demo
from saint_elmo_backend.mandates.models import Mandate


@pytest.fixture
async def seeded(reference_data, session) -> None:
    session.add_all(Category(code=code) for code in demo.DAIRY_CATEGORY_CODES)
    await demo.seed_demo(session)
    await session.commit()


async def test_token_works_on_search_and_mandate_and_names_its_issuer(seeded, session, client):
    issued = await command.issue_token_for_seeded_agent(
        session, agent_name="dairy-restock", buyer_admin_email=demo.HOTEL_BUYER_ADMIN_EMAIL
    )
    await session.commit()

    search = await client.post("/api/v1/products/search", json={}, headers=bearer(issued))
    mandate = await client.get("/api/v1/agents/me/mandate", headers=bearer(issued))

    assert search.status_code == 200, search.text
    assert mandate.status_code == 200, mandate.text
    assert mandate.json()["agent"]["name"] == "dairy-restock"

    credential = await session.scalar(
        select(AgentCredential).where(AgentCredential.jti == issued.jti)
    )
    issuer = await session.scalar(select(User).where(User.email == demo.HOTEL_BUYER_ADMIN_EMAIL))
    assert credential.created_by_user_id == issuer.id
    assert issued.expires_at - datetime.now(UTC) > timedelta(days=29, hours=23)


async def test_research_only_preset_cannot_place_orders(seeded, session):
    await command.issue_token_for_seeded_agent(
        session,
        agent_name="dairy-restock",
        buyer_admin_email=demo.HOTEL_BUYER_ADMIN_EMAIL,
        preset=ScopePreset.RESEARCH_ONLY,
    )

    credential = await session.scalar(select(AgentCredential))
    assert sorted(credential.scopes) == [
        "audit:read",
        "catalog:read",
        "mandate:read",
        "offers:read",
        "order:read",
    ]


async def test_buyer_admin_of_another_buyer_organisation_is_refused(seeded, session):
    with pytest.raises(command.IssueTokenRefusedError, match="another buyer organisation"):
        await command.issue_token_for_seeded_agent(
            session,
            agent_name="dairy-restock",
            buyer_admin_email=demo.HOSPITAL_BUYER_ADMIN_EMAIL,
        )

    assert await session.scalar(select(AgentCredential)) is None


async def test_agent_without_a_mandate_is_refused(seeded, session):
    await session.execute(delete(Mandate))

    with pytest.raises(command.IssueTokenRefusedError, match="no mandate"):
        await command.issue_token_for_seeded_agent(
            session, agent_name="dairy-restock", buyer_admin_email=demo.HOTEL_BUYER_ADMIN_EMAIL
        )


def test_presets_are_named_on_the_command_line():
    args = command.parse_args(["dairy-restock", "admin@example.com", "Research only"])

    assert args.preset is ScopePreset.RESEARCH_ONLY
    assert command.parse_args(["dairy-restock", "admin@example.com"]).preset is (
        ScopePreset.PURCHASING
    )


def test_unknown_preset_is_refused_on_the_command_line():
    with pytest.raises(SystemExit):
        command.parse_args(["dairy-restock", "admin@example.com", "Everything"])
