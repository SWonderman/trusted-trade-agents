"""
Buyer admins managing their buyer organisation's agents and Agent tokens, over HTTP.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from sqlalchemy import select

from saint_elmo_backend.accounts.enums import Role
from saint_elmo_backend.accounts.tests.factories import (
    make_organization,
    make_user,
    user_session_headers,
)
from saint_elmo_backend.agents.enums import AgentStatus
from saint_elmo_backend.agents.models import Agent
from saint_elmo_backend.agents.tests.factories import bearer, make_agent
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.audit.models import AuditEvent
from saint_elmo_backend.mandates import crud as mandate_crud

AGENTS_URL = "/api/v1/agents"
MANDATE_URL = "/api/v1/agents/me/mandate"
QUOTES_URL = "/api/v1/quotes"


def tokens_url(agent) -> str:
    return f"{AGENTS_URL}/{agent.public_id}/tokens"


async def test_buyer_admin_lists_their_agents(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    restock = await make_agent(session, organization, name="dairy-restock")
    await make_agent(session, organization, name="old-bot", status=AgentStatus.DISABLED)
    await make_agent(session, await make_organization(session), name="someone-elses")
    await session.commit()

    response = await client.get(AGENTS_URL, headers=user_session_headers(admin))

    assert response.status_code == 200, response.text
    agents = {agent["name"]: agent for agent in response.json()["items"]}
    assert set(agents) == {"dairy-restock", "old-bot"}
    assert agents["dairy-restock"] == {
        "id": str(restock.public_id),
        "name": "dairy-restock",
        "status": "ACTIVE",
    }
    assert agents["old-bot"]["status"] == "DISABLED"


async def test_issued_token_carries_the_preset_mandate_and_default_expiry(
    clean_db, session, client
):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    await session.commit()
    mandate = await mandate_crud.get_mandate_for_agent(
        session, organization_id=organization.id, agent_id=agent.id
    )
    assert mandate is not None

    response = await client.post(
        tokens_url(agent),
        json={"label": "laptop", "preset": "Research only"},
        headers=user_session_headers(admin),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    claims = jwt.decode(body["token"], options={"verify_signature": False})
    assert claims["sub"] == str(agent.public_id)
    assert claims["mandate_id"] == str(mandate.public_id)
    assert claims["jti"] == body["jti"]
    assert claims["scope"] == "audit:read catalog:read mandate:read offers:read order:read"
    assert body["scopes"] == [
        "audit:read",
        "catalog:read",
        "mandate:read",
        "offers:read",
        "order:read",
    ]
    expected_exp = datetime.now(UTC) + timedelta(days=7)
    assert abs(claims["exp"] - expected_exp.timestamp()) < 60
    assert datetime.fromisoformat(body["expiresAt"]).timestamp() == pytest.approx(
        claims["exp"], abs=1
    )


async def test_issued_token_works_at_once_within_its_scopes(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    await session.commit()

    issued = await client.post(
        tokens_url(agent),
        json={"label": "laptop", "scopes": ["mandate:read"], "expiresInDays": 30},
        headers=user_session_headers(admin),
    )
    assert issued.status_code == 201, issued.text
    token = issued.json()["token"]

    assert (await client.get(MANDATE_URL, headers=bearer(token))).status_code == 200
    denied = await client.post(QUOTES_URL, json={}, headers=bearer(token))
    assert denied.status_code == 403, denied.text
    assert denied.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.parametrize(
    "body",
    [
        {"label": "x", "preset": "Purchasing", "expiresInDays": 31},
        {"label": "x", "preset": "Purchasing", "expiresInDays": 0},
        {"label": "x", "scopes": ["catalog:read", "order:approve"]},
        {"label": "x", "preset": "Everything"},
        {"label": "x", "preset": "Purchasing", "scopes": ["catalog:read"]},
        {"label": "x"},
        {"label": "x", "scopes": []},
    ],
    ids=[
        "expiry-over-30-days",
        "expiry-zero",
        "unknown-scope",
        "unknown-preset",
        "scopes-and-preset",
        "neither",
        "no-scopes",
    ],
)
async def test_invalid_token_request_is_rejected(clean_db, session, client, body):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    await session.commit()

    response = await client.post(tokens_url(agent), json=body, headers=user_session_headers(admin))

    assert response.status_code == 422, response.text


async def test_agent_without_a_mandate_gets_no_token(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = Agent(name="no-mandate", organization=organization)
    session.add(agent)
    await session.commit()

    response = await client.post(
        tokens_url(agent),
        json={"label": "x", "preset": "Purchasing"},
        headers=user_session_headers(admin),
    )

    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "MANDATE_REQUIRED"


async def test_unknown_agent_is_not_found(clean_db, session, client):
    admin = await make_user(session, await make_organization(session))
    await session.commit()

    response = await client.post(
        f"{AGENTS_URL}/{uuid4()}/tokens",
        json={"label": "x", "preset": "Purchasing"},
        headers=user_session_headers(admin),
    )

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "AGENT_NOT_FOUND"


async def test_listing_tokens_never_shows_their_value(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    other_agent = await make_agent(session, organization)
    await session.commit()
    headers = user_session_headers(admin)
    issued = (
        await client.post(
            tokens_url(agent),
            json={"label": "laptop", "preset": "Research only", "expiresInDays": 3},
            headers=headers,
        )
    ).json()
    await client.post(
        tokens_url(other_agent), json={"label": "other", "preset": "Purchasing"}, headers=headers
    )
    await client.get(MANDATE_URL, headers=bearer(issued["token"]))

    response = await client.get(tokens_url(agent), headers=headers)

    assert response.status_code == 200, response.text
    assert issued["token"] not in response.text
    [token] = response.json()["items"]
    assert token["jti"] == issued["jti"]
    assert token["label"] == "laptop"
    assert token["scopes"] == issued["scopes"]
    assert token["expiresAt"] == issued["expiresAt"]
    assert token["createdBy"] == {
        "id": str(admin.public_id),
        "name": f"{admin.first_name} {admin.last_name}",
    }
    assert token["createdAt"] is not None
    assert token["lastUsedAt"] is not None
    assert token["revokedAt"] is None
    assert "token" not in token


async def _issue(client, admin, agent, preset: str = "Purchasing") -> dict:
    response = await client.post(
        tokens_url(agent),
        json={"label": "laptop", "preset": preset},
        headers=user_session_headers(admin),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_revoked_token_is_refused_on_the_next_request(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    await session.commit()
    issued = await _issue(client, admin, agent)
    kept = await _issue(client, admin, agent)
    assert (await client.get(MANDATE_URL, headers=bearer(issued["token"]))).status_code == 200

    response = await client.delete(
        f"{tokens_url(agent)}/{issued['jti']}", headers=user_session_headers(admin)
    )

    assert response.status_code == 200, response.text
    assert response.json()["jti"] == issued["jti"]
    assert response.json()["revokedAt"] is not None
    refused = await client.get(MANDATE_URL, headers=bearer(issued["token"]))
    assert refused.status_code == 401, refused.text
    assert (await client.get(MANDATE_URL, headers=bearer(kept["token"]))).status_code == 200


async def test_revoking_twice_keeps_the_first_revocation(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    await session.commit()
    issued = await _issue(client, admin, agent)
    url = f"{tokens_url(agent)}/{issued['jti']}"
    first = await client.delete(url, headers=user_session_headers(admin))

    second = await client.delete(url, headers=user_session_headers(admin))

    assert second.status_code == 200, second.text
    assert second.json()["revokedAt"] == first.json()["revokedAt"]


async def test_revoking_a_token_of_another_agent_is_not_found(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    other_agent = await make_agent(session, organization)
    await session.commit()
    issued = await _issue(client, admin, other_agent)

    response = await client.delete(
        f"{tokens_url(agent)}/{issued['jti']}", headers=user_session_headers(admin)
    )

    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "AGENT_TOKEN_NOT_FOUND"
    assert (await client.get(MANDATE_URL, headers=bearer(issued["token"]))).status_code == 200


async def test_disabling_an_agent_refuses_all_its_tokens(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    other_agent = await make_agent(session, organization)
    await session.commit()
    tokens = [await _issue(client, admin, agent) for _ in range(2)]
    other = await _issue(client, admin, other_agent)

    response = await client.post(
        f"{AGENTS_URL}/{agent.public_id}/disable", headers=user_session_headers(admin)
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"id": str(agent.public_id), "name": agent.name, "status": "DISABLED"}
    for token in tokens:
        refused = await client.get(MANDATE_URL, headers=bearer(token["token"]))
        assert refused.status_code == 401, refused.text
    assert (await client.get(MANDATE_URL, headers=bearer(other["token"]))).status_code == 200


async def test_disabling_twice_succeeds(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization, status=AgentStatus.DISABLED)
    await session.commit()

    response = await client.post(
        f"{AGENTS_URL}/{agent.public_id}/disable", headers=user_session_headers(admin)
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "DISABLED"


def _management_requests(agent, jti) -> list[tuple[str, str, dict | None]]:
    return [
        ("GET", AGENTS_URL, None),
        ("POST", tokens_url(agent), {"label": "x", "preset": "Purchasing"}),
        ("GET", tokens_url(agent), None),
        ("DELETE", f"{tokens_url(agent)}/{jti}", None),
        ("POST", f"{AGENTS_URL}/{agent.public_id}/disable", None),
    ]


async def test_another_buyer_organisation_cannot_see_or_touch_these_agents(
    clean_db, session, client
):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    outsider = await make_user(session, await make_organization(session))
    await session.commit()
    issued = await _issue(client, admin, agent)

    for method, url, body in _management_requests(agent, issued["jti"]):
        response = await client.request(
            method, url, json=body, headers=user_session_headers(outsider)
        )
        if url == AGENTS_URL:
            assert response.status_code == 200, response.text
            assert response.json()["items"] == []
        else:
            assert response.status_code == 404, f"{method} {url}: {response.text}"

    assert (await client.get(MANDATE_URL, headers=bearer(issued["token"]))).status_code == 200
    [token] = (await client.get(tokens_url(agent), headers=user_session_headers(admin))).json()[
        "items"
    ]
    assert token["revokedAt"] is None


@pytest.mark.parametrize("who", ["agent-token", "approver"])
async def test_only_buyer_admins_manage_agents(clean_db, session, client, who):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    approver = await make_user(session, organization, role=Role.APPROVER)
    await session.commit()
    issued = await _issue(client, admin, agent)
    headers = bearer(issued["token"]) if who == "agent-token" else user_session_headers(approver)

    for method, url, body in _management_requests(agent, issued["jti"]):
        response = await client.request(method, url, json=body, headers=headers)
        assert response.status_code == 403, f"{method} {url}: {response.text}"
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"


async def _audit_events(session, organization) -> list[AuditEvent]:
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.org_id == organization.id)
        .order_by(AuditEvent.created_at, AuditEvent.id)
    )
    return list(await session.scalars(stmt))


async def test_issue_revoke_and_disable_are_audited_once(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    await session.commit()
    headers = user_session_headers(admin)
    issued = await _issue(client, admin, agent, preset="Research only")
    live = await _issue(client, admin, agent)
    for _ in range(2):
        await client.delete(f"{tokens_url(agent)}/{issued['jti']}", headers=headers)
        await client.post(f"{AGENTS_URL}/{agent.public_id}/disable", headers=headers)

    events = await _audit_events(session, organization)

    assert [event.event_type for event in events] == [
        AuditEventType.AGENT_TOKEN_ISSUED,
        AuditEventType.AGENT_TOKEN_ISSUED,
        AuditEventType.AGENT_TOKEN_REVOKED,
        AuditEventType.AGENT_DISABLED,
    ]
    assert all(event.user_id == admin.id and event.agent_id == agent.id for event in events)
    issue_event, _, revoke_event, disable_event = events
    assert issue_event.subject_public_id == agent.public_id
    expires_at = datetime.fromisoformat(issued["expiresAt"])
    assert {**issue_event.payload, "expiresAt": None} == {
        "jti": issued["jti"],
        "label": "laptop",
        "scopes": issued["scopes"],
        "expiresAt": None,
    }
    assert datetime.fromisoformat(issue_event.payload["expiresAt"]) == expires_at
    assert revoke_event.payload == {
        "jti": issued["jti"],
        "scopes": issued["scopes"],
        "expiresAt": issue_event.payload["expiresAt"],
    }
    # Only the tokens disabling cut off: the revoked one already was
    assert disable_event.payload == {"cutOffJtis": [live["jti"]]}


async def test_concurrent_revokes_and_disables_are_audited_once(clean_db, session, client):
    organization = await make_organization(session)
    admin = await make_user(session, organization)
    agent = await make_agent(session, organization)
    await session.commit()
    headers = user_session_headers(admin)
    issued = await _issue(client, admin, agent)

    revokes = await asyncio.gather(
        *(client.delete(f"{tokens_url(agent)}/{issued['jti']}", headers=headers) for _ in range(5))
    )
    disables = await asyncio.gather(
        *(client.post(f"{AGENTS_URL}/{agent.public_id}/disable", headers=headers) for _ in range(5))
    )

    assert all(response.status_code == 200 for response in [*revokes, *disables])
    event_types = [event.event_type for event in await _audit_events(session, organization)]
    assert event_types.count(AuditEventType.AGENT_TOKEN_REVOKED) == 1
    assert event_types.count(AuditEventType.AGENT_DISABLED) == 1
