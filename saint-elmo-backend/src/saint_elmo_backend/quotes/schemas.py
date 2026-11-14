from datetime import date, datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import UUID4, Field, model_validator

from saint_elmo_backend.core.schema import CamelBaseModel, DecimalNumber
from saint_elmo_backend.offers.schemas import OfferOut
from saint_elmo_backend.policy.dtos import PolicyReason
from saint_elmo_backend.policy.enums import PolicyOutcome, PolicyReasonCode, Severity
from saint_elmo_backend.quotes.dtos import QuoteLineRequest, QuoteRequest
from saint_elmo_backend.quotes.enums import QuoteStatus
from saint_elmo_backend.quotes.models import Quote, QuoteLine

# Request

MAX_LINES = 50
MAX_TEXT_LENGTH = 2000


class QuoteLineIn(CamelBaseModel):
    product_code: str = Field(min_length=1, max_length=20, examples=["463038"])
    quantity: Decimal = Field(gt=0, examples=[1000])
    unit: str | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        description="`L`, `KG`, or one of the product's unit codes such as `KI` or `ST`. "
        "Without it the quantity is in the product's sales unit",
        examples=["L"],
    )
    substitutes_for: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        description="The product code this line is a substitute for. The line is then "
        "judged by the mandate's substitution rules, and its price compared with that "
        "product's",
    )

    @model_validator(mode="after")
    def _not_its_own_substitute(self) -> Self:
        if self.substitutes_for == self.product_code:
            raise ValueError("a line can't substitute for its own product")
        return self

    def to_line_request(self) -> QuoteLineRequest:
        return QuoteLineRequest(
            product_code=self.product_code,
            quantity=self.quantity,
            unit=self.unit.upper() if self.unit else None,
            substitutes_for=self.substitutes_for,
        )


class QuoteIn(CamelBaseModel):
    deliver_by: date = Field(
        description="Delivery date, already resolved by the agent (e.g. 'by Monday')"
    )
    lines: list[QuoteLineIn] = Field(min_length=1, max_length=MAX_LINES)
    buyer_request: str = Field(
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="The need as the buyer stated it. Kept with the quote; never affects "
        "the policy",
        examples=["1,000 litres of lactose-free milk by Monday"],
    )
    rationale: str = Field(
        min_length=1,
        max_length=MAX_TEXT_LENGTH,
        description="Why the agent chose these lines. Shown to approvers; never affects the policy",
    )
    previous_quote_id: UUID4 | None = Field(
        default=None,
        description="The quote this one revises, so attempts for one buyer request stay connected",
    )

    def to_quote_request(self) -> QuoteRequest:
        return QuoteRequest(
            deliver_by=self.deliver_by,
            lines=tuple(line.to_line_request() for line in self.lines),
            buyer_request=self.buyer_request,
            rationale=self.rationale,
            previous_quote_id=self.previous_quote_id,
        )


# Response


class PolicyReasonOut(CamelBaseModel):
    code: PolicyReasonCode
    severity: Severity
    line_ref: str | None = Field(description="The line's position (from 1); null for the quote")
    message: str = Field(description="One plain-English sentence for approvers")
    facts: dict[str, Any] = Field(
        description="The numbers behind the reason, e.g. available vs ordered amounts"
    )

    @classmethod
    def from_reason(cls, reason: PolicyReason) -> "PolicyReasonOut":
        return cls(
            code=reason.code,
            severity=reason.severity,
            line_ref=reason.line_ref,
            message=reason.message,
            # Amounts go out as JSON numbers, like every other amount in the API
            facts={
                key: float(value) if isinstance(value, Decimal) else value
                for key, value in reason.facts.items()
            },
        )


class QuoteLineOut(OfferOut):
    """
    The line's offer, as `POST /offers` returns it, plus what the quote adds.
    """

    position: int
    substitutes_for: str | None
    outcome: PolicyOutcome = Field(description="The most severe outcome of the line's reasons")
    reasons: list[PolicyReasonOut]

    @classmethod
    def from_quote_line(cls, line: QuoteLine) -> "QuoteLineOut":
        return cls.model_validate(
            {
                **line.offer,
                "position": line.position,
                "substitutesFor": line.substitutes_for,
                "outcome": line.outcome,
                "reasons": line.reasons,
            }
        )


class QuoteTotals(CamelBaseModel):
    net: DecimalNumber
    gross: DecimalNumber
    currency: str


class DepositOut(CamelBaseModel):
    material_code: str
    quantity: DecimalNumber = Field(description="Deposit units for the whole quote")
    unit: str


class QuotePolicy(CamelBaseModel):
    outcome: PolicyOutcome = Field(
        description="What placing an order from this quote would give if live data hasn't changed"
    )
    reasons: list[PolicyReasonOut] = Field(description="Lines in order, then the quote's own")
    mandate_version: int = Field(description="The mandate version the quote was judged against")


class QuoteResponse(CamelBaseModel):
    quote_id: UUID4
    status: QuoteStatus
    created_at: datetime
    expires_at: datetime = Field(
        description="The earliest of the lines' price validity, their closing time for "
        "deliverBy, and the quote time-to-live"
    )
    deliver_by: date
    lines: list[QuoteLineOut]
    totals: QuoteTotals = Field(description="Excluding deposits")
    deposits: list[DepositOut] = Field(
        description="Returnable packaging charged on top; Valio Aimo gives no deposit price"
    )
    policy: QuotePolicy
    buyer_request: str
    rationale: str
    previous_quote_id: UUID4 | None

    @classmethod
    def from_quote(cls, quote: Quote, status: QuoteStatus) -> "QuoteResponse":
        return cls(
            quote_id=quote.public_id,
            status=status,
            created_at=quote.created_at,
            expires_at=quote.expires_at,
            deliver_by=quote.deliver_by,
            lines=[QuoteLineOut.from_quote_line(line) for line in quote.lines],
            totals=QuoteTotals(
                net=quote.net_total, gross=quote.gross_total, currency=quote.currency
            ),
            deposits=[DepositOut.model_validate(deposit) for deposit in quote.deposits],
            policy=QuotePolicy(
                outcome=quote.outcome,
                reasons=[PolicyReasonOut.model_validate(r) for r in quote.reasons],
                mandate_version=quote.mandate_version,
            ),
            buyer_request=quote.buyer_request,
            rationale=quote.rationale,
            previous_quote_id=quote.previous_quote.public_id if quote.previous_quote else None,
        )
