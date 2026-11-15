"""
Reading the audit trail back over HTTP: the flat event list and one order's trail.
"""

from dataclasses import replace
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts.enums import Role
from saint_elmo_backend.accounts.models import Organization
from saint_elmo_backend.accounts.tests.factories import (
    make_organization,
    make_user,
    user_session_headers,
)
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.agents.models import Agent
from saint_elmo_backend.agents.tests.factories import bearer, issue_token, make_agent
from saint_elmo_backend.audit import services as audit_services
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.quotes.tests.conftest import DAIRY_RESTOCK
from saint_elmo_backend.valio_aimo.testing import EILA_10L

EVENTS_URL = "/api/v1/audit-events"
QUOTES_URL = "/api/v1/quotes"
ORDERS_URL = "/api/v1/orders"
DELIVER_BY = "2030-06-03"
MILK_LINE = {"productCode": EILA_10L, "quantity": 1000, "unit": "L"}

PURCHASING = (Scope.QUOTE_CREATE, Scope.ORDER_PLACE, Scope.ORDER_READ, Scope.AUDIT_READ)
AUTO_APPROVED_MILK = replace(DAIRY_RESTOCK, auto_approve_up_to=Decimal("2000"))


async def _agent(
    session: AsyncSession,
    organization: Organization,
    *,
    mandate=DAIRY_RESTOCK,
    scopes=PURCHASING,
) -> tuple[Agent, dict[str, str]]:
    agent = await make_agent(session, organization, mandate=mandate)
    token = await issue_token(session, agent, scopes=scopes)
    await session.commit()
    return agent, bearer(token)


async def _user(session: AsyncSession, organization: Organization, role=Role.BUYER_ADMIN):
    user = await make_user(session, organization, role=role)
    await session.commit()
    return user, user_session_headers(user)


async def _quote(client: AsyncClient, headers: dict[str, str], **extra) -> dict:
    response = await client.post(
        QUOTES_URL,
        json={
            "deliverBy": DELIVER_BY,
            "lines": [MILK_LINE],
            "buyerRequest": "1,000 litres of lactose-free milk by Monday",
            "rationale": "Eila 10 l novobox is lactose free and sold per 20 l case",
            **extra,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _order(client: AsyncClient, headers: dict[str, str], quote_id: str) -> dict:
    response = await client.post(ORDERS_URL, json={"quoteId": quote_id}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def _events(client: AsyncClient, headers: dict[str, str], **params) -> dict:
    response = await client.get(EVENTS_URL, params=params, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_a_buyer_admin_reads_the_organisations_events_newest_first(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    agent, agent_headers = await _agent(session, organization, mandate=AUTO_APPROVED_MILK)
    quote = await _quote(client, agent_headers)
    order = await _order(client, agent_headers, quote["quoteId"])
    _, admin = await _user(session, organization)
    issued = await client.post(
        f"/api/v1/agents/{agent.public_id}/tokens",
        json={"label": "laptop", "preset": "Research only"},
        headers=admin,
    )
    assert issued.status_code == 201, issued.text

    body = await _events(client, admin)

    types = [event["type"] for event in body["items"]]
    assert types == [
        "AGENT_TOKEN_ISSUED",
        "ORDER_PLACED",
        "ORDER_CONFIRMED",
        "ORDER_RECHECKED",
        "ORDER_REQUESTED",
        "QUOTE_CREATED",
    ]
    assert body["nextCursor"] is None
    issued, placed, _, rechecked, _, quoted = body["items"]
    assert placed["actor"] == {"kind": "system", "id": None, "name": "system"}
    assert placed["subjectId"] == order["orderId"]
    assert quoted["actor"] == {"kind": "agent", "id": str(agent.public_id), "name": agent.name}
    assert quoted["subjectId"] == quote["quoteId"]
    assert quoted["summary"] == (
        f"{agent.name} quoted 50 KI of {EILA_10L} for €1,565.50: within the mandate"
    )
    assert quoted["outcome"] == "AUTO_APPROVE"
    assert "STOCK_UNKNOWN" in quoted["reasonCodes"]
    assert quoted["payload"]["quoteId"] == quote["quoteId"]
    assert rechecked["outcome"] == "AUTO_APPROVE"
    assert placed["outcome"] is None and placed["reasonCodes"] is None
    # A buyer admin's action on an agent is credited to the admin, not the agent
    assert issued["actor"]["kind"] == "user"
    assert issued["subjectId"] == str(agent.public_id)
    assert issued["summary"].endswith(
        f'issued the Agent token "laptop" to {agent.name} '
        "(audit:read, catalog:read, mandate:read, offers:read, order:read), expiring "
        + issued["payload"]["expiresAt"][:10]
    )


async def test_events_filter_by_type_agent_subject_and_time(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    milk, milk_headers = await _agent(session, organization)
    _, other_headers = await _agent(session, organization)
    first = await _quote(client, milk_headers)
    await _quote(client, other_headers)
    _, admin = await _user(session, organization)

    quotes = await _events(client, admin, type="QUOTE_CREATED")
    of_milk = await _events(client, admin, agentId=str(milk.public_id))
    about_first = await _events(client, admin, subject=first["quoteId"])
    at = about_first["items"][0]["at"]
    from_then = await _events(client, admin, **{"from": at})
    before_then = await _events(client, admin, to=at)

    assert len(quotes["items"]) == 2
    assert [e["subjectId"] for e in of_milk["items"]] == [first["quoteId"]]
    assert [e["subjectId"] for e in about_first["items"]] == [first["quoteId"]]
    assert len(from_then["items"]) == 2
    assert before_then["items"] == []


async def test_events_page_newest_first_with_a_cursor(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    _, agent_headers = await _agent(session, organization)
    quote_ids = [(await _quote(client, agent_headers))["quoteId"] for _ in range(3)]
    _, admin = await _user(session, organization)

    first = await _events(client, admin, limit=2)
    second = await _events(client, admin, limit=2, cursor=first["nextCursor"])

    assert [e["subjectId"] for e in first["items"]] == quote_ids[:0:-1]
    assert [e["subjectId"] for e in second["items"]] == quote_ids[:1]
    assert second["nextCursor"] is None


async def test_a_cursor_the_list_never_returned_is_refused(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    _, admin = await _user(session, organization)

    response = await client.get(EVENTS_URL, params={"cursor": "not-a-cursor"}, headers=admin)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_more_than_200_events_per_page_is_refused(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    _, admin = await _user(session, organization)

    response = await client.get(EVENTS_URL, params={"limit": 201}, headers=admin)

    assert response.status_code == 422


async def test_an_agent_token_without_audit_read_is_refused(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    agent, headers = await _agent(
        session, organization, scopes=(Scope.QUOTE_CREATE, Scope.ORDER_PLACE, Scope.ORDER_READ)
    )
    quote = await _quote(client, headers)
    order = await _order(client, headers, quote["quoteId"])

    listed = await client.get(EVENTS_URL, headers=headers)
    trail = await client.get(f"{ORDERS_URL}/{order['orderId']}/trail", headers=headers)

    for response in (listed, trail):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PERMISSION_DENIED"


async def _approved_order(
    client: AsyncClient, session: AsyncSession, organization: Organization
) -> tuple[Agent, dict[str, str], dict]:
    """
    An order over the auto-approve limit, approved by an approver.
    """
    agent, headers = await _agent(session, organization)
    quote = await _quote(client, headers)
    order = await _order(client, headers, quote["quoteId"])
    assert order["status"] == "PENDING_APPROVAL"
    _, approver = await _user(session, organization, role=Role.APPROVER)
    response = await client.post(
        f"{ORDERS_URL}/{order['orderId']}/approve", json={"note": "Weekend"}, headers=approver
    )
    assert response.json()["status"] == "PLACED", response.text
    return agent, headers, order


async def test_an_agent_sees_its_own_events_and_human_decisions_on_its_orders(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    _, headers, order = await _approved_order(client, session, organization)
    _, someone_else = await _agent(session, organization)
    await _quote(client, someone_else)

    body = await _events(client, headers)

    assert [(e["type"], e["actor"]["kind"]) for e in body["items"]] == [
        ("ORDER_PLACED", "system"),
        ("ORDER_APPROVED", "user"),
        # Not the approver's re-check: the agent didn't act in it
        ("ORDER_PENDING_APPROVAL", "agent"),
        ("ORDER_RECHECKED", "agent"),
        ("ORDER_REQUESTED", "agent"),
        ("QUOTE_CREATED", "agent"),
    ]
    assert body["items"][1]["summary"].endswith('approved the order: "Weekend"')


async def test_another_organisations_events_and_orders_are_never_returned(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    _, _, order = await _approved_order(client, session, organization)
    elsewhere = await make_organization(session)
    _, their_agent = await _agent(session, elsewhere)
    _, their_admin = await _user(session, elsewhere)

    for headers in (their_admin, their_agent):
        assert (await _events(client, headers))["items"] == []
        assert (await _events(client, headers, subject=order["orderId"]))["items"] == []
        trail = await client.get(f"{ORDERS_URL}/{order['orderId']}/trail", headers=headers)
        assert trail.status_code == 404
        assert trail.json()["error"]["code"] == "ORDER_NOT_FOUND"


async def test_an_agent_cant_read_another_agents_order_trail(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    _, _, order = await _approved_order(client, session, organization)
    _, colleague = await _agent(session, organization)

    response = await client.get(f"{ORDERS_URL}/{order['orderId']}/trail", headers=colleague)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORDER_NOT_FOUND"


async def _request_substitutes(session: AsyncSession, agent: Agent, product_code: str) -> None:
    """
    Arranged directly: the substitutes endpoint needs a candidate catalogue this
    trail doesn't care about.
    """
    await audit_services.record_event(
        session,
        organization_id=agent.org_id,
        event_type=AuditEventType.SUBSTITUTES_REQUESTED,
        agent_id=agent.id,
        payload={"productCode": product_code, "candidates": []},
    )
    await session.commit()


async def test_an_order_trail_runs_from_the_first_quote_to_the_sign_off(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    agent, headers = await _agent(session, organization)
    await _request_substitutes(session, agent, "999999")  # before any quote
    first = await _quote(client, headers)
    await _request_substitutes(session, agent, EILA_10L)
    await _request_substitutes(session, agent, "999999")  # another product
    revised = await _quote(client, headers, previousQuoteId=first["quoteId"])
    unrelated = await _quote(client, headers)
    order = await _order(client, headers, revised["quoteId"])
    _, approver = await _user(session, organization, role=Role.APPROVER)
    await client.post(f"{ORDERS_URL}/{order['orderId']}/approve", headers=approver)
    await _request_substitutes(session, agent, EILA_10L)  # after the order's last event
    _, admin = await _user(session, organization)

    response = await client.get(f"{ORDERS_URL}/{order['orderId']}/trail", headers=admin)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["orderId"] == order["orderId"]
    assert [(e["type"], e["subjectId"]) for e in body["items"]] == [
        ("QUOTE_CREATED", first["quoteId"]),
        ("SUBSTITUTES_REQUESTED", None),
        ("QUOTE_CREATED", revised["quoteId"]),
        ("ORDER_REQUESTED", order["orderId"]),
        ("ORDER_RECHECKED", order["orderId"]),
        ("ORDER_PENDING_APPROVAL", order["orderId"]),
        ("ORDER_RECHECKED", order["orderId"]),
        ("ORDER_APPROVED", order["orderId"]),
        ("ORDER_PLACED", order["orderId"]),
    ]
    assert unrelated["quoteId"] not in [e["subjectId"] for e in body["items"]]
    assert body["items"][1]["payload"]["productCode"] == EILA_10L
    assert body["items"][6]["actor"]["kind"] == "user"
    assert "before approving" in body["items"][6]["summary"]


async def test_an_agent_reads_its_own_order_trail_without_the_approvers_recheck(
    client: AsyncClient, session: AsyncSession, organization: Organization
):
    _, headers, order = await _approved_order(client, session, organization)

    response = await client.get(f"{ORDERS_URL}/{order['orderId']}/trail", headers=headers)

    assert response.status_code == 200, response.text
    assert [e["type"] for e in response.json()["items"]] == [
        "QUOTE_CREATED",
        "ORDER_REQUESTED",
        "ORDER_RECHECKED",
        "ORDER_PENDING_APPROVAL",
        "ORDER_APPROVED",
        "ORDER_PLACED",
    ]


async def test_both_endpoints_are_in_the_openapi_schema(client: AsyncClient):
    paths = (await client.get("/openapi.json")).json()["paths"]

    listed = paths["/api/v1/audit-events"]["get"]
    assert {"200", "401", "403", "422"} <= set(listed["responses"])
    assert {"AgentToken": ["audit:read"]} in listed["security"]
    trail = paths["/api/v1/orders/{order_id}/trail"]["get"]
    assert {"200", "401", "403", "404"} <= set(trail["responses"])
    assert {"AgentToken": ["audit:read"]} in trail["security"]
