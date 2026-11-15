"""
The plain English sentence each audit event is read back with.
"""

import pytest

from saint_elmo_backend.audit.enums import AuditEventType
from saint_elmo_backend.audit.summaries import summarize

# The milk example: 50 cases of Eila 10 l over the 1,500 € auto-approve limit
MILK_POLICY = {
    "outcome": "NEEDS_HUMAN",
    "reasons": [
        {"code": "STOCK_UNKNOWN", "severity": "INFO", "lineRef": "1"},
        {"code": "OVER_AUTO_APPROVE_LIMIT", "severity": "NEEDS_HUMAN", "lineRef": None},
    ],
    "mandateVersion": 1,
}
MILK_LINES = [
    {
        "lineRef": "1",
        "offer": {"productCode": "463038", "salesUnit": "KI", "quantity": {"salesUnits": 50.0}},
    }
]
MILK_QUOTE = {
    "quoteId": "bdf1a93f-b551-47f9-8a9a-b8569a28db5f",
    "lines": MILK_LINES,
    "policy": MILK_POLICY,
    "totals": {"net": 1565.5, "gross": 1784.5, "currency": "EUR"},
}


def test_a_quote_reads_as_what_was_quoted_for_how_much_and_the_verdict():
    summary = summarize(AuditEventType.QUOTE_CREATED, MILK_QUOTE, actor="dairy-restock")

    assert summary == (
        "dairy-restock quoted 50 KI of 463038 for €1,565.50: "
        "needs a human (over the auto-approve limit)"
    )


def test_a_human_approval_names_the_approver_and_their_note():
    summary = summarize(
        AuditEventType.ORDER_APPROVED,
        {"status": "APPROVED", "note": "Weekend event", "approver": "user:Ada Lovelace"},
        actor="Ada Lovelace",
    )

    assert summary == 'Ada Lovelace approved the order: "Weekend event"'


def test_an_agent_token_event_names_the_agent_it_is_about():
    summary = summarize(
        AuditEventType.AGENT_TOKEN_ISSUED,
        {
            "jti": "x",
            "label": "laptop",
            "scopes": ["catalog:read", "offers:read"],
            "expiresAt": "2026-11-22T10:00:00+00:00",
        },
        actor="Ada Lovelace",
        agent="dairy-restock",
    )

    assert summary == (
        'Ada Lovelace issued the Agent token "laptop" to dairy-restock '
        "(catalog:read, offers:read), expiring 2026-11-22"
    )


@pytest.mark.parametrize("event_type", list(AuditEventType))
def test_every_event_type_has_a_sentence_even_from_an_empty_payload(event_type):
    summary = summarize(event_type, {}, actor="dairy-restock", agent="dairy-restock")

    assert summary.strip()
