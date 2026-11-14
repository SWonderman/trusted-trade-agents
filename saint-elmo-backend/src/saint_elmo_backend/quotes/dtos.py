from dataclasses import dataclass
from datetime import date
from uuid import UUID

from saint_elmo_backend.policy.dtos import LineRequest


@dataclass(frozen=True, slots=True)
class QuoteRequest:
    deliver_by: date
    lines: tuple[LineRequest, ...]
    # Free text: stored and shown, never read by the policy
    buyer_request: str
    rationale: str
    previous_quote_id: UUID | None = None
