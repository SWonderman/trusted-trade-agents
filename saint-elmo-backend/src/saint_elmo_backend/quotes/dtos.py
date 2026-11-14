from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class QuoteLineRequest:
    """
    `unit` None means the quantity is in the product's sales unit. `substitutes_for` is
    the product code this line is a substitute for.
    """

    product_code: str
    quantity: Decimal
    unit: str | None = None
    substitutes_for: str | None = None


@dataclass(frozen=True, slots=True)
class QuoteRequest:
    deliver_by: date
    lines: tuple[QuoteLineRequest, ...]
    # Free text: stored and shown, never read by the policy
    buyer_request: str
    rationale: str
    previous_quote_id: UUID | None = None
