from datetime import date, datetime
from typing import Any

from pydantic import UUID4, Field

from saint_elmo_backend.core.schema import CamelBaseModel
from saint_elmo_backend.offers.schemas import DepositOut, Totals
from saint_elmo_backend.orders.enums import CHECK_AGAIN_AFTER_SECONDS, OrderStatus
from saint_elmo_backend.orders.models import Order
from saint_elmo_backend.policy.enums import PolicyOutcome
from saint_elmo_backend.policy.schemas import JudgedLineOut, PolicyReasonOut
from saint_elmo_backend.quotes.schemas import MAX_TEXT_LENGTH

# Request


class OrderIn(CamelBaseModel):
    quote_id: UUID4 = Field(
        description="The quote to order. Also the idempotency key: a quote gives at most "
        "one order, so retrying after a timeout is safe"
    )


class DecisionIn(CamelBaseModel):
    note: str | None = Field(
        default=None,
        max_length=MAX_TEXT_LENGTH,
        description="Why the approver decided so; shown with the order and kept in the audit trail",
    )


# Response


class OrderPolicy(CamelBaseModel):
    outcome: PolicyOutcome = Field(description="The policy outcome of the latest live re-check")
    reasons: list[PolicyReasonOut] = Field(description="Lines in order, then the order's own")
    mandate_version: int = Field(description="The mandate version the re-check judged against")


class OrderChange(CamelBaseModel):
    line_ref: str = Field(description="The line's position (from 1)")
    field: str = Field(
        description="unitPrice (net per sales unit), availableAmount, earliestDate, "
        "closingTime or salesBlocked"
    )
    quoted: Any = Field(description="The value the quote was judged on")
    now: Any = Field(description="The live value the order was judged on")


class StatusChangeOut(CamelBaseModel):
    status: OrderStatus
    at: datetime
    by: str = Field(
        description='Whose request led to it: "agent:<name>" or "user:<first and last '
        'name>"; "system" for placing a confirmed or approved order',
        examples=["agent:dairy-restock"],
    )


class OrderAgent(CamelBaseModel):
    id: UUID4
    name: str


class OrderResponse(CamelBaseModel):
    order_id: UUID4
    quote_id: UUID4
    status: OrderStatus
    created_at: datetime
    agent: OrderAgent
    deliver_by: date
    lines: list[JudgedLineOut] = Field(
        description="Each line's live offer at the latest re-check, and its judgement"
    )
    totals: Totals = Field(description="Excluding deposits")
    deposits: list[DepositOut]
    policy: OrderPolicy
    changes: list[OrderChange] = Field(
        description="Where the live data the order was judged on differs from the quote's. "
        "The order follows the live result"
    )
    buyer_request: str
    rationale: str
    status_history: list[StatusChangeOut] = Field(description="Oldest first")
    approver_note: str | None = Field(description="The approver's note, once decided")
    decided_at: datetime | None
    check_again_after_seconds: int | None = Field(
        description="While PENDING_APPROVAL: poll the order again after this many seconds"
    )

    @classmethod
    def from_order(cls, order: Order) -> "OrderResponse":
        quote = order.quote
        return cls(
            order_id=order.public_id,
            quote_id=quote.public_id,
            status=order.status,
            created_at=order.created_at,
            agent=OrderAgent(id=order.agent.public_id, name=order.agent.name),
            deliver_by=quote.deliver_by,
            lines=[JudgedLineOut.from_line(line) for line in order.lines],
            totals=Totals(net=order.net_total, gross=order.gross_total, currency=order.currency),
            deposits=[DepositOut.model_validate(deposit) for deposit in order.deposits],
            policy=OrderPolicy(
                outcome=order.outcome,
                reasons=[PolicyReasonOut.model_validate(r) for r in order.reasons],
                mandate_version=order.mandate_version,
            ),
            changes=[OrderChange.model_validate(change) for change in order.changes],
            buyer_request=quote.buyer_request,
            rationale=quote.rationale,
            status_history=[
                StatusChangeOut(status=change.status, at=change.at, by=change.by)
                for change in order.status_history
            ],
            approver_note=order.approver_note,
            decided_at=order.decided_at,
            check_again_after_seconds=CHECK_AGAIN_AFTER_SECONDS
            if order.status is OrderStatus.PENDING_APPROVAL
            else None,
        )


class OrderListResponse(CamelBaseModel):
    total: int
    items: list[OrderResponse] = Field(description="Most recent first")
