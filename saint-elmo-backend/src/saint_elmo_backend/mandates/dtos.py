from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.enums import AllergenStrictness
from saint_elmo_backend.mandates.enums import SpendPeriod, SubstitutionPolicy


@dataclass(frozen=True, slots=True)
class CategorySpendCap:
    category_code: str
    cap: Decimal


@dataclass(frozen=True, slots=True)
class MandateTerms:
    """
    The limits a buyer organization sets for one agent. Amounts are EUR excluding VAT.

    An empty allow-list allows anything.
    """

    # Spend
    max_order_total: Decimal
    period_spend_cap: Decimal
    spend_period: SpendPeriod
    # Approval: a compliant order below this total needs no human
    auto_approve_up_to: Decimal
    # Substitution
    substitution_policy: SubstitutionPolicy
    max_substitute_price_increase_pct: Decimal
    # Per spend period
    category_spend_caps: tuple[CategorySpendCap, ...] = ()
    # Assortment
    allowed_category_codes: tuple[str, ...] = ()
    blocked_category_codes: tuple[str, ...] = ()
    allowed_vendors: tuple[str, ...] = ()
    blocked_vendors: tuple[str, ...] = ()
    # ISO 3166-1 alpha-2, lowercase, as in the catalogue
    allowed_countries_of_origin: tuple[str, ...] = ()
    # Requirements
    required_claims: tuple[ClaimCode, ...] = ()
    required_labels: tuple[str, ...] = ()
    required_diets: tuple[str, ...] = ()
    excluded_allergens: tuple[str, ...] = ()
    allergen_strictness: AllergenStrictness = AllergenStrictness.CONTAINS
    # Delivery
    later_delivery_needs_approval: bool = True
    min_delivery_reliability: Decimal | None = None

    def __post_init__(self) -> None:
        if self.auto_approve_up_to > self.max_order_total:
            raise ValueError("auto_approve_up_to must not exceed max_order_total")


@dataclass(frozen=True, slots=True)
class PeriodSpend:
    """
    What the agent's orders committed in the current spend period, which runs from
    `period_start` (inclusive) to `period_end` (exclusive).
    """

    period_start: datetime
    period_end: datetime
    committed: Decimal
    remaining: Decimal


@dataclass(frozen=True, slots=True)
class AgentMandate:
    public_id: UUID
    version: int
    terms: MandateTerms
    period_spend: PeriodSpend
