"""
Placing orders from quotes, deciding them and reading them back, exercised over HTTP on
the fake Valio Aimo API.
"""

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts.enums import Role
from saint_elmo_backend.accounts.models import Organization
from saint_elmo_backend.accounts.tests.factories import (
    make_organization,
    make_user,
    user_session_headers,
)
from saint_elmo_backend.agents.enums import Scope
from saint_elmo_backend.api.v1.routes import quotes as quotes_route
from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.audit.models import AuditEvent
from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.orders.models import Order
from saint_elmo_backend.quotes.tests.conftest import DAIRY_RESTOCK, Authenticate
from saint_elmo_backend.valio_aimo.testing import EILA_10L, FakeValioAimoApi

QUOTES_URL = "/api/v1/quotes"
ORDERS_URL = "/api/v1/orders"
MANDATE_URL = "/api/v1/agents/me/mandate"
# A Monday far enough ahead that no closing time has passed
DELIVER_BY = "2030-06-03"

# 50 cases of milk at 31.31 €: 1,565.50 €
MILK_LINE = {"productCode": EILA_10L, "quantity": 1000, "unit": "L"}
MILK_TOTAL = 1565.5

ORDERING = (Scope.QUOTE_CREATE, Scope.ORDER_PLACE, Scope.ORDER_READ)
# Auto-approves the milk example
AUTO_APPROVED_MILK = replace(DAIRY_RESTOCK, auto_approve_up_to=Decimal("2000"))


async def _quote(client: AsyncClient, *lines: dict) -> dict:
    response = await client.post(
        QUOTES_URL,
        json={
            "deliverBy": DELIVER_BY,
            "lines": list(lines or [MILK_LINE]),
            "buyerRequest": "1,000 litres of lactose-free milk by Monday",
            "rationale": "Eila 10 l novobox is lactose free and sold per 20 l case",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _order(client: AsyncClient, quote_id: str) -> dict:
    response = await client.post(ORDERS_URL, json={"quoteId": quote_id})
    assert response.status_code == 201, response.text
    return response.json()


async def test_a_compliant_quote_is_ordered_and_placed(
    client: AsyncClient, authenticate: Authenticate
):
    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING)
    quote = await _quote(client)

    order = await _order(client, quote["quoteId"])

    assert order["quoteId"] == quote["quoteId"]
    assert order["status"] == "PLACED"
    assert order["policy"]["outcome"] == "AUTO_APPROVE"
    assert order["policy"]["mandateVersion"] == 1
    assert order["totals"] == {"net": MILK_TOTAL, "gross": 1784.5, "currency": "EUR"}
    [line] = order["lines"]
    assert line["productCode"] == EILA_10L
    assert line["quantity"]["salesUnits"] == 50.0
    assert order["changes"] == []
    assert order["checkAgainAfterSeconds"] is None
    assert [(entry["status"], entry["by"]) for entry in order["statusHistory"]] == [
        ("CONFIRMED", "agent:" + order["agent"]["name"]),
        ("PLACED", "system"),
    ]


async def test_a_quote_over_the_auto_approve_limit_waits_for_approval(
    client: AsyncClient, authenticate: Authenticate
):
    # DAIRY_RESTOCK auto-approves up to 1,500 €
    await authenticate(DAIRY_RESTOCK, scopes=ORDERING)
    quote = await _quote(client)

    order = await _order(client, quote["quoteId"])

    assert order["status"] == "PENDING_APPROVAL"
    assert order["checkAgainAfterSeconds"] == 30
    assert "OVER_AUTO_APPROVE_LIMIT" in [r["code"] for r in order["policy"]["reasons"]]
    assert order["buyerRequest"] == "1,000 litres of lactose-free milk by Monday"
    assert [entry["status"] for entry in order["statusHistory"]] == ["PENDING_APPROVAL"]


async def test_ordering_the_same_quote_twice_gives_the_first_order_and_no_second(
    client: AsyncClient, authenticate: Authenticate, session: AsyncSession
):
    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING)
    quote = await _quote(client)
    first = await _order(client, quote["quoteId"])

    retry = await client.post(ORDERS_URL, json={"quoteId": quote["quoteId"]})

    assert retry.status_code == 409
    error = retry.json()["error"]
    assert error["code"] == "QUOTE_ALREADY_ORDERED"
    assert error["details"] == {"orderId": first["orderId"]}
    assert await session.scalar(select(func.count()).select_from(Order)) == 1


async def test_an_expired_quote_cant_be_ordered(
    client: AsyncClient, authenticate: Authenticate, monkeypatch: pytest.MonkeyPatch
):
    settings = get_settings().model_copy(update={"quote_ttl_minutes": 0})
    monkeypatch.setattr(quotes_route, "get_settings", lambda: settings)
    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING)
    quote = await _quote(client)

    response = await client.post(ORDERS_URL, json={"quoteId": quote["quoteId"]})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "QUOTE_EXPIRED"


async def test_an_agent_cant_order_another_agents_quote(
    client: AsyncClient, authenticate: Authenticate
):
    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING)
    quote = await _quote(client)

    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING)
    response = await client.post(ORDERS_URL, json={"quoteId": quote["quoteId"]})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "QUOTE_NOT_FOUND"


async def test_the_order_is_judged_on_fresh_prices_and_says_what_changed(
    client: AsyncClient, authenticate: Authenticate, fake_api: FakeValioAimoApi
):
    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING)
    # The quote's price is still cached when the order comes in
    quote = await _quote(client)
    fake_api.change_price(EILA_10L, value=41.00, comparison=2.05)

    order = await _order(client, quote["quoteId"])

    assert order["changes"] == [
        {"lineRef": "1", "field": "unitPrice", "quoted": 31.31, "now": 41.0}
    ]
    # 50 cases at 41 € is over the 2,000 € per order
    assert order["totals"]["net"] == 2050.0
    assert order["status"] == "REJECTED"
    assert "OVER_ORDER_LIMIT" in [r["code"] for r in order["policy"]["reasons"]]


async def _pending_order(client: AsyncClient, authenticate: Authenticate) -> dict:
    await authenticate(DAIRY_RESTOCK, scopes=ORDERING)
    order = await _order(client, (await _quote(client))["quoteId"])
    assert order["status"] == "PENDING_APPROVAL"
    return order


async def _approver(session: AsyncSession, organization: Organization) -> dict[str, str]:
    user = await make_user(session, organization, role=Role.APPROVER)
    await session.commit()
    return user_session_headers(user)


@pytest.mark.parametrize("decision", ["approve", "reject"])
async def test_an_agent_token_with_every_scope_cant_decide_an_order(
    client: AsyncClient, authenticate: Authenticate, decision: str
):
    order = await _pending_order(client, authenticate)
    await authenticate(DAIRY_RESTOCK, scopes=tuple(Scope))

    response = await client.post(f"{ORDERS_URL}/{order['orderId']}/{decision}", json={})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


async def test_an_approver_approves_a_pending_order_and_it_is_placed(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
):
    order = await _pending_order(client, authenticate)
    approver = await _approver(session, organization)

    response = await client.post(
        f"{ORDERS_URL}/{order['orderId']}/approve",
        json={"note": "Weekend event, approved"},
        headers=approver,
    )

    assert response.status_code == 200, response.text
    approved = response.json()
    assert approved["status"] == "PLACED"
    assert approved["approverNote"] == "Weekend event, approved"
    assert approved["checkAgainAfterSeconds"] is None
    history = [(entry["status"], entry["by"].split(":")[0]) for entry in approved["statusHistory"]]
    assert history == [
        ("PENDING_APPROVAL", "agent"),
        ("APPROVED", "user"),
        ("PLACED", "system"),
    ]


async def test_approving_past_the_closing_time_rejects_the_order(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
    fake_api: FakeValioAimoApi,
):
    order = await _pending_order(client, authenticate)
    approver = await _approver(session, organization)
    fake_api.change_availability(EILA_10L, closing_time="2026-01-01T15:00:00+0200")

    response = await client.post(f"{ORDERS_URL}/{order['orderId']}/approve", headers=approver)

    assert response.status_code == 200, response.text
    rejected = response.json()
    assert rejected["status"] == "REJECTED"
    assert "CLOSING_TIME_PASSED" in [r["code"] for r in rejected["policy"]["reasons"]]
    assert {"lineRef": "1", "field": "closingTime"}.items() <= rejected["changes"][0].items()
    # The approver's request led to it, so the step and the audit trail name them
    assert rejected["statusHistory"][-1]["status"] == "REJECTED"
    assert rejected["statusHistory"][-1]["by"].startswith("user:")
    assert rejected["approverNote"] is None
    session.expire_all()
    rejection = (await _audit_trail(session, order["orderId"]))[-1]
    assert rejection.event_type is AuditEventType.ORDER_REJECTED
    assert rejection.user_id is not None


async def test_an_approver_rejects_a_pending_order_with_a_note(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
):
    order = await _pending_order(client, authenticate)
    approver = await _approver(session, organization)

    response = await client.post(
        f"{ORDERS_URL}/{order['orderId']}/reject", json={"note": "Too much"}, headers=approver
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REJECTED"
    assert response.json()["approverNote"] == "Too much"


async def test_only_a_pending_order_can_be_decided(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
):
    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING)
    placed = await _order(client, (await _quote(client))["quoteId"])
    approver = await _approver(session, organization)

    response = await client.post(f"{ORDERS_URL}/{placed['orderId']}/approve", headers=approver)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_NOT_PENDING"


async def test_orders_are_read_only_by_their_agent_and_their_buyer_organisation(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
):
    other_organization = await make_organization(session)
    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING, organization=other_organization)
    theirs = await _order(client, (await _quote(client))["quoteId"])
    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING)
    colleagues = await _order(client, (await _quote(client))["quoteId"])
    await authenticate(DAIRY_RESTOCK, scopes=ORDERING)
    ours = await _order(client, (await _quote(client))["quoteId"])

    # The agent: its own orders only
    listed = (await client.get(ORDERS_URL)).json()
    assert listed["total"] == 1
    assert [o["orderId"] for o in listed["items"]] == [ours["orderId"]]
    assert listed["items"][0]["statusHistory"] == ours["statusHistory"]
    for other in (theirs, colleagues):
        response = await client.get(f"{ORDERS_URL}/{other['orderId']}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ORDER_NOT_FOUND"

    # A user: every order of their buyer organisation, most recent first
    user = await _approver(session, organization)
    listed = (await client.get(ORDERS_URL, headers=user)).json()
    assert [o["orderId"] for o in listed["items"]] == [ours["orderId"], colleagues["orderId"]]
    pending = (
        await client.get(ORDERS_URL, params={"status": "PENDING_APPROVAL"}, headers=user)
    ).json()
    assert [o["orderId"] for o in pending["items"]] == [ours["orderId"]]
    read = await client.get(f"{ORDERS_URL}/{ours['orderId']}", headers=user)
    assert read.json()["checkAgainAfterSeconds"] == 30
    assert (await client.get(f"{ORDERS_URL}/{theirs['orderId']}", headers=user)).status_code == 404


# Two milk orders (2 × 1,565.50 €) don't fit in the period
CAPPED_AT_3000 = replace(DAIRY_RESTOCK, period_spend_cap=Decimal("3000"))


async def test_a_pending_order_counts_toward_the_period_cap_of_the_next(
    client: AsyncClient, authenticate: Authenticate
):
    await authenticate(CAPPED_AT_3000, scopes=ORDERING)
    first = await _order(client, (await _quote(client))["quoteId"])
    assert first["status"] == "PENDING_APPROVAL"

    second = await _order(client, (await _quote(client))["quoteId"])

    over_cap = next(r for r in second["policy"]["reasons"] if r["code"] == "OVER_PERIOD_CAP")
    assert over_cap["facts"] == {"periodSpend": MILK_TOTAL, "orderTotal": MILK_TOTAL, "cap": 3000.0}


async def test_the_mandate_shows_what_pending_and_placed_orders_commit_but_not_rejected_ones(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
):
    await authenticate(CAPPED_AT_3000, scopes=(*ORDERING, Scope.MANDATE_READ))
    pending = await _order(client, (await _quote(client))["quoteId"])

    spend = (await client.get(MANDATE_URL)).json()["periodSpend"]
    assert spend["committed"] == MILK_TOTAL
    assert spend["remaining"] == 3000 - MILK_TOTAL

    approver = await _approver(session, organization)
    await client.post(f"{ORDERS_URL}/{pending['orderId']}/reject", headers=approver)

    assert (await client.get(MANDATE_URL)).json()["periodSpend"]["committed"] == 0


async def test_approving_doesnt_count_the_order_against_itself(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
):
    # One milk order fits in the cap, but not twice
    await authenticate(replace(DAIRY_RESTOCK, period_spend_cap=Decimal("2000")), scopes=ORDERING)
    pending = await _order(client, (await _quote(client))["quoteId"])
    approver = await _approver(session, organization)

    response = await client.post(f"{ORDERS_URL}/{pending['orderId']}/approve", headers=approver)

    assert "OVER_PERIOD_CAP" not in [r["code"] for r in response.json()["policy"]["reasons"]]


async def _audit_trail(session: AsyncSession, order_id: str) -> list[AuditEvent]:
    stmt = select(AuditEvent).where(AuditEvent.subject_public_id == UUID(order_id))
    return list(await session.scalars(stmt.order_by(AuditEvent.id)))


async def test_the_audit_trail_records_the_request_the_recheck_and_every_status(
    client: AsyncClient,
    authenticate: Authenticate,
    fake_api: FakeValioAimoApi,
    session: AsyncSession,
):
    await authenticate(AUTO_APPROVED_MILK, scopes=ORDERING)
    quote = await _quote(client)
    fake_api.change_price(EILA_10L, value=32.00, comparison=1.60)

    order = await _order(client, quote["quoteId"])

    events = await _audit_trail(session, order["orderId"])
    assert [event.event_type for event in events] == [
        AuditEventType.ORDER_REQUESTED,
        AuditEventType.ORDER_RECHECKED,
        AuditEventType.ORDER_CONFIRMED,
        AuditEventType.ORDER_PLACED,
    ]
    recheck = events[1].payload
    assert recheck["changes"] == order["changes"]
    assert recheck["policy"]["mandateVersion"] == 1
    assert recheck["lines"][0]["offer"]["price"]["perSalesUnit"]["net"] == 32.0
    assert events[3].agent_id is None


async def test_a_human_rejection_is_audited_with_the_approver_and_note(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
):
    order = await _pending_order(client, authenticate)
    approver = await _approver(session, organization)

    await client.post(
        f"{ORDERS_URL}/{order['orderId']}/reject", json={"note": "Too much"}, headers=approver
    )

    session.expire_all()
    rejection = (await _audit_trail(session, order["orderId"]))[-1]
    assert rejection.event_type is AuditEventType.ORDER_REJECTED_BY_HUMAN
    assert rejection.user_id is not None
    assert rejection.payload["note"] == "Too much"
    assert rejection.payload["by"].startswith("user:")


async def test_a_reason_the_approver_hasnt_seen_keeps_the_order_pending_until_approved_again(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
    fake_api: FakeValioAimoApi,
):
    # Pending only for being over the auto-approve limit; the period cap still holds
    await authenticate(replace(DAIRY_RESTOCK, period_spend_cap=Decimal("1700")), scopes=ORDERING)
    order = await _order(client, (await _quote(client))["quoteId"])
    assert "OVER_PERIOD_CAP" not in [r["code"] for r in order["policy"]["reasons"]]
    approver = await _approver(session, organization)
    # 50 cases at 34.50 € is 1,725 €, now over the period cap
    fake_api.change_price(EILA_10L, value=34.50, comparison=1.73)

    first = await client.post(f"{ORDERS_URL}/{order['orderId']}/approve", headers=approver)

    assert first.status_code == 200, first.text
    still_pending = first.json()
    assert still_pending["status"] == "PENDING_APPROVAL"
    assert "OVER_PERIOD_CAP" in [r["code"] for r in still_pending["policy"]["reasons"]]
    assert still_pending["approverNote"] is None

    # Approving again, with the new reason shown, places it
    second = await client.post(f"{ORDERS_URL}/{order['orderId']}/approve", headers=approver)

    assert second.json()["status"] == "PLACED"


async def test_an_order_whose_total_grew_since_the_approver_saw_it_stays_pending(
    client: AsyncClient,
    authenticate: Authenticate,
    session: AsyncSession,
    organization: Organization,
    fake_api: FakeValioAimoApi,
):
    # Pending at 1,565.50 € for being over the 1,500 € auto-approve limit
    order = await _pending_order(client, authenticate)
    approver = await _approver(session, organization)
    # Still only over the auto-approve limit, but now at 1,600 €
    fake_api.change_price(EILA_10L, value=32.00, comparison=1.60)

    first = await client.post(f"{ORDERS_URL}/{order['orderId']}/approve", headers=approver)

    assert first.status_code == 200, first.text
    still_pending = first.json()
    assert still_pending["status"] == "PENDING_APPROVAL"
    assert still_pending["totals"]["net"] == 1600.0
    assert [r["code"] for r in still_pending["policy"]["reasons"]] == [
        r["code"] for r in order["policy"]["reasons"]
    ]

    # Approving again, with the new total shown, places it
    second = await client.post(f"{ORDERS_URL}/{order['orderId']}/approve", headers=approver)

    assert second.json()["status"] == "PLACED"
