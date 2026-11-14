from decimal import Decimal
from typing import Any, Protocol

from pydantic import Field

from saint_elmo_backend.core.schema import CamelBaseModel
from saint_elmo_backend.offers.schemas import OfferOut
from saint_elmo_backend.policy.dtos import PolicyReason
from saint_elmo_backend.policy.enums import PolicyOutcome, PolicyReasonCode, Severity


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


class JudgedLine(Protocol):
    """
    A stored quote or order line: its offer and reasons as the API's JSON.
    """

    position: int
    substitutes_for: str | None
    outcome: PolicyOutcome
    offer: dict[str, Any]
    reasons: list[dict[str, Any]]


class JudgedLineOut(OfferOut):
    """
    The line's offer, as `POST /offers` returns it, plus the policy's judgement of it.
    """

    position: int
    substitutes_for: str | None
    outcome: PolicyOutcome = Field(description="The most severe outcome of the line's reasons")
    reasons: list[PolicyReasonOut]

    @classmethod
    def from_line(cls, line: JudgedLine) -> "JudgedLineOut":
        return cls.model_validate(
            {
                **line.offer,
                "position": line.position,
                "substitutesFor": line.substitutes_for,
                "outcome": line.outcome,
                "reasons": line.reasons,
            }
        )
