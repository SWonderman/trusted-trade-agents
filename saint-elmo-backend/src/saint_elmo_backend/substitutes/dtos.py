from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from saint_elmo_backend.catalog.dtos import ClaimCode, ProductFilters
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.offers.dtos import OfferLine
from saint_elmo_backend.policy.dtos import PolicyJudgement
from saint_elmo_backend.substitutes.enums import SubstitutesReasonCode
from saint_elmo_backend.substitutes.ranking import RankedCandidate


@dataclass(frozen=True, slots=True)
class SubstitutesRequest:
    """
    `quantity` None ranks without a need; `unit` None means the quantity is in the
    original's sales unit. `filters` holds only requirement filters, which are added to
    the mandate's and never replace them.
    """

    quantity: Decimal | None = None
    unit: str | None = None
    deliver_by: date | None = None
    filters: ProductFilters = ProductFilters()
    limit: int = 3
    language: Language = Language.EN


@dataclass(frozen=True, slots=True)
class TradeOffs:
    """
    A candidate against the original. A delta is None when either side is unknown.
    """

    price_per_buyer_unit_delta_pct: Decimal | None
    # Days; positive when the candidate arrives later
    earliest_date_delta: int | None
    reliability_delta: Decimal | None
    claims_kept: list[ClaimCode]
    claims_lost: list[ClaimCode]
    labels_gained: list[str]
    labels_lost: list[str]
    # kg CO2-eq per kg, of the two product-group estimates
    carbon_footprint_delta: Decimal | None


@dataclass(frozen=True, slots=True)
class Substitute:
    ranked: RankedCandidate
    # As the response shows it: with a quantity only when one was requested
    offer: OfferLine
    trade_offs: TradeOffs
    # The candidate judged as a substitute line for the original; commits to nothing
    policy_preview: PolicyJudgement

    @property
    def product_code(self) -> str:
        return self.ranked.facts.product_code

    @property
    def curated(self) -> bool:
        return self.ranked.facts.curated


@dataclass(frozen=True, slots=True)
class Substitutes:
    original: OfferLine
    # The requested deliverBy, or the default the offers were evaluated for
    deliver_by: date
    # The unit candidates were compared and priced in
    buyer_unit: str
    evaluated_at: datetime
    candidates: list[Substitute]
    reason_codes: tuple[SubstitutesReasonCode, ...]
    # The mandate version the previews were judged against
    mandate_version: int
