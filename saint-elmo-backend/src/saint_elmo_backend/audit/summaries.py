"""
One plain English sentence per audit event, rendered at read time from its type and
payload (never stored), e.g. "dairy-restock quoted 50 KI of 463038 for €1,565.50: needs
a human (over the auto-approve limit)".

Payloads are read defensively: older events may lack a key, and a missing value leaves
the sentence shorter rather than failing the read.
"""

from collections.abc import Callable
from typing import Any

from saint_elmo_backend.audit.enums import AuditEventType

type Payload = dict[str, Any]
type Renderer = Callable[[Payload, str, str | None], str]

# Reason codes that read badly when simply lower-cased
_REASON_PHRASES = {
    "OVER_AUTO_APPROVE_LIMIT": "over the auto-approve limit",
    "OVER_ORDER_LIMIT": "over the order limit",
    "OVER_PERIOD_CAP": "over the period spend cap",
    "OVER_CATEGORY_CAP": "over the category spend cap",
    "CLOSING_TIME_PASSED": "the closing time has passed",
    "NO_PRICE": "no price",
    "BELOW_MIN_RELIABILITY": "below the minimum delivery reliability",
}

_VERDICTS = {
    "AUTO_APPROVE": "within the mandate",
    "NEEDS_HUMAN": "needs a human",
    "REJECT": "rejected",
}


def summarize(
    event_type: AuditEventType, payload: Payload, *, actor: str, agent: str | None = None
) -> str:
    """
    `actor` is who acted (an agent's or user's name, or "system"); `agent` is the agent
    the event is about, which differs from the actor for a buyer admin's action on an agent.

    Raises `KeyError` for an event type without a renderer.
    """
    return _RENDERERS[event_type](payload, actor, agent)


def lifted_policy(payload: Payload) -> tuple[str | None, list[str] | None]:
    """
    The policy outcome and reason codes an event's payload holds, if any: those of a
    judgement against the mandate (`policy`), or a substitute request's own `reasonCodes`.
    """
    policy = payload.get("policy")
    if isinstance(policy, dict):
        reasons = policy.get("reasons")
        codes = [reason["code"] for reason in reasons] if reasons is not None else None
        return policy.get("outcome"), codes
    codes = payload.get("reasonCodes")
    return None, list(codes) if codes is not None else None


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'s' if count != 1 else ''}"


def _number(value: Any) -> str:
    number = float(value)
    return f"{number:,.0f}" if number.is_integer() else f"{number:,}"


def _money(totals: Any) -> str | None:
    if not isinstance(totals, dict) or totals.get("net") is None:
        return None
    symbol = "€" if totals.get("currency", "EUR") == "EUR" else f"{totals['currency']} "
    return f"{symbol}{float(totals['net']):,.2f}"


def _reason(code: str) -> str:
    return _REASON_PHRASES.get(code, code.lower().replace("_", " "))


def _verdict(policy: Any) -> str | None:
    """
    The outcome, with the reasons that decided it: "needs a human (over the auto-approve limit)".
    """
    if not isinstance(policy, dict) or policy.get("outcome") not in _VERDICTS:
        return None
    outcome = policy["outcome"]
    deciding = [
        _reason(reason["code"])
        for reason in policy.get("reasons") or []
        if reason.get("severity") == outcome and reason.get("code")
    ]
    verdict = _VERDICTS[outcome]
    return f"{verdict} ({', '.join(deciding)})" if deciding else verdict


def _quoted_lines(payload: Payload) -> str | None:
    """
    "50 KI of 463038", in sales units as quoted; the request's own units without an offer.
    """
    parts = []
    for line in payload.get("lines") or []:
        offer = line.get("offer") or {}
        sales_units = (offer.get("quantity") or {}).get("salesUnits")
        if offer.get("productCode") and sales_units is not None:
            parts.append(
                f"{_number(sales_units)} {offer.get('salesUnit', '')} of {offer['productCode']}"
            )
    if not parts:
        for line in (payload.get("request") or {}).get("lines") or []:
            if line.get("productCode") and line.get("quantity") is not None:
                parts.append(
                    f"{_number(line['quantity'])} {line.get('unit', '')} of {line['productCode']}"
                )
    return ", ".join(parts).replace("  ", " ") or None


def _joined(head: str, *tail: str | None, sep: str = ": ") -> str:
    """
    `head` followed by whichever of `tail` are present.
    """
    rest = [part for part in tail if part]
    return sep.join([head, *rest])


def _note(payload: Payload) -> str | None:
    note = payload.get("note")
    return f'"{note}"' if note else None


def _quote_created(payload: Payload, actor: str, agent: str | None) -> str:
    what = _quoted_lines(payload) or "a quote"
    money = _money(payload.get("totals"))
    head = f"{actor} quoted {what}" + (f" for {money}" if money else "")
    if (payload.get("request") or {}).get("previousQuoteId"):
        head += ", revising an earlier quote"
    return _joined(head, _verdict(payload.get("policy")))


def _substitutes_requested(payload: Payload, actor: str, agent: str | None) -> str:
    code = payload.get("productCode")
    head = f"{actor} asked for substitutes" + (f" for {code}" if code else "")
    candidates = payload.get("candidates")
    if candidates is None:
        return head
    if not candidates:
        return f"{head} and got none"
    top = candidates[0].get("productCode")
    count = len(candidates)
    got = f"{head} and got {_plural(count, 'candidate')}"
    return got + (f", best {top}" if top else "")


def _order_requested(payload: Payload, actor: str, agent: str | None) -> str:
    quote_id = payload.get("quoteId")
    return f"{actor} asked to place an order" + (f" from quote {quote_id[:8]}" if quote_id else "")


def _order_rechecked(payload: Payload, actor: str, agent: str | None) -> str:
    when = " before approving" if payload.get("approval") else ""
    head = f"{actor} re-checked the order on live data{when}"
    money = _money(payload.get("totals"))
    if money:
        head += f": {money}"
    changes = payload.get("changes") or []
    changed = f"{_plural(len(changes), 'change')} since the quote" if changes else None
    return _joined(head, _verdict(payload.get("policy")), changed, sep=", " if money else ": ")


def _order_confirmed(payload: Payload, actor: str, agent: str | None) -> str:
    return "The order was confirmed: the policy approved it automatically"


def _order_pending_approval(payload: Payload, actor: str, agent: str | None) -> str:
    return "The order is waiting for a human to approve it"


def _order_approved(payload: Payload, actor: str, agent: str | None) -> str:
    return _joined(f"{actor} approved the order", _note(payload))


def _order_placed(payload: Payload, actor: str, agent: str | None) -> str:
    return "The order was placed in the order book"


def _order_rejected(payload: Payload, actor: str, agent: str | None) -> str:
    when = " when it was re-checked for approval" if payload.get("approver") else ""
    return f"The policy rejected the order{when}"


def _order_rejected_by_human(payload: Payload, actor: str, agent: str | None) -> str:
    return _joined(f"{actor} rejected the order", _note(payload))


def _agent_token_issued(payload: Payload, actor: str, agent: str | None) -> str:
    label = payload.get("label")
    token = f'the Agent token "{label}"' if label else "an Agent token"
    head = f"{actor} issued {token}" + (f" to {agent}" if agent else "")
    scopes = payload.get("scopes")
    if scopes:
        head += f" ({', '.join(scopes)})"
    expires = payload.get("expiresAt")
    return head + (f", expiring {expires[:10]}" if expires else "")


def _agent_token_revoked(payload: Payload, actor: str, agent: str | None) -> str:
    return f"{actor} revoked an Agent token" + (f" of {agent}" if agent else "")


def _agent_disabled(payload: Payload, actor: str, agent: str | None) -> str:
    head = f"{actor} disabled {agent or 'an agent'}"
    cut_off = payload.get("cutOffJtis")
    if not cut_off:
        return head
    return f"{head}, cutting off {_plural(len(cut_off), 'live token')}"


_RENDERERS: dict[AuditEventType, Renderer] = {
    AuditEventType.QUOTE_CREATED: _quote_created,
    AuditEventType.SUBSTITUTES_REQUESTED: _substitutes_requested,
    AuditEventType.ORDER_REQUESTED: _order_requested,
    AuditEventType.ORDER_RECHECKED: _order_rechecked,
    AuditEventType.ORDER_CONFIRMED: _order_confirmed,
    AuditEventType.ORDER_PENDING_APPROVAL: _order_pending_approval,
    AuditEventType.ORDER_APPROVED: _order_approved,
    AuditEventType.ORDER_PLACED: _order_placed,
    AuditEventType.ORDER_REJECTED: _order_rejected,
    AuditEventType.ORDER_REJECTED_BY_HUMAN: _order_rejected_by_human,
    AuditEventType.AGENT_TOKEN_ISSUED: _agent_token_issued,
    AuditEventType.AGENT_TOKEN_REVOKED: _agent_token_revoked,
    AuditEventType.AGENT_DISABLED: _agent_disabled,
}
