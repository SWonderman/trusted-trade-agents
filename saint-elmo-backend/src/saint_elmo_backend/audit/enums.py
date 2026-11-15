from enum import StrEnum


class AuditEventType(StrEnum):
    QUOTE_CREATED = "QUOTE_CREATED"
    # An agent asked for ranked substitutes, with the candidates returned
    SUBSTITUTES_REQUESTED = "SUBSTITUTES_REQUESTED"
    # An agent asked to place an order from a quote
    ORDER_REQUESTED = "ORDER_REQUESTED"
    # Live data re-checked and judged, at placing and at approval, with what changed
    ORDER_RECHECKED = "ORDER_RECHECKED"
    # The order entered that status
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_PENDING_APPROVAL = "ORDER_PENDING_APPROVAL"
    # A human approved it, with the approver and note
    ORDER_APPROVED = "ORDER_APPROVED"
    ORDER_PLACED = "ORDER_PLACED"
    # The policy rejected it
    ORDER_REJECTED = "ORDER_REJECTED"
    # A human rejected it, with the approver and note
    ORDER_REJECTED_BY_HUMAN = "ORDER_REJECTED_BY_HUMAN"
    # A buyer admin issued an Agent token, with its jti, scopes and expiry
    AGENT_TOKEN_ISSUED = "AGENT_TOKEN_ISSUED"
    # A buyer admin revoked an Agent token, with its jti, scopes and expiry
    AGENT_TOKEN_REVOKED = "AGENT_TOKEN_REVOKED"
    # A buyer admin disabled an agent, with the live tokens that cut off
    AGENT_DISABLED = "AGENT_DISABLED"
