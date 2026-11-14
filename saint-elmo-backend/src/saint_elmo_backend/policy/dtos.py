from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.enums import AllergenContainment
from saint_elmo_backend.mandates.dtos import MandateTerms
from saint_elmo_backend.offers.enums import LogisticModel
from saint_elmo_backend.offers.quantity import ConvertedQuantity
from saint_elmo_backend.policy.enums import PolicyOutcome, PolicyReasonCode, Severity


@dataclass(frozen=True, slots=True)
class LineRequest:
    """
    One line to price and judge, as a quote requested it. `unit` None means the quantity is in the product's sales unit. `substitutes_for` is
    the product code this line is a substitute for.
    """

    product_code: str
    quantity: Decimal
    unit: str | None = None
    substitutes_for: str | None = None


@dataclass(frozen=True, slots=True)
class ProductFacts:
    """
    What the catalog declares about a product. An allergen without an entry, a claim,
    label or diet not listed, and a None origin or reliability are unknown, which is
    never the same as free-from or as having it.
    """

    category_code: str
    vendor: str
    # ISO 3166-1 alpha-2, lowercase
    country_of_origin: str | None = None
    claims: tuple[ClaimCode, ...] = ()
    labels: tuple[str, ...] = ()
    diets: tuple[str, ...] = ()
    allergens: Mapping[str, AllergenContainment] = field(default_factory=dict)
    delivery_reliability: Decimal | None = None


@dataclass(frozen=True, slots=True)
class LineOffer:
    """
    The live offer for one line's product and quantity.
    """

    # Net EUR per sales unit; None when the price API gave none
    unit_price: Decimal | None
    # Product or schedule line sales-blocked
    sales_blocked: bool
    # None when there is no schedule line at all
    earliest_date: date | None
    closing_time: datetime | None
    # As the offer judged it (it may ignore passed closing times in a demo)
    closing_time_passed: bool
    logistic_model: LogisticModel | None
    # In sales units; None when unknown
    available_amount: Decimal | None
    quantity: ConvertedQuantity
    # Net EUR; None when the quantity or price is unknown
    line_total: Decimal | None

    @property
    def buyer_unit(self) -> str:
        return self.quantity.requested_unit

    @property
    def price_per_buyer_unit(self) -> Decimal | None:
        """
        Net EUR per buyer unit; None when the price or the conversion is unknown.
        """
        if self.unit_price is None or self.quantity.sales_units is None:
            return None
        conversion = self.quantity.conversion
        # No conversion: the buyer unit is the sales unit itself
        return self.unit_price / conversion.per_sales_unit if conversion else self.unit_price


@dataclass(frozen=True, slots=True)
class SubstitutedProduct:
    """
    The product a substitute line replaces, with its own offer for the same requested
    quantity, so prices can be compared per buyer unit.
    """

    product_code: str
    offer: LineOffer


@dataclass(frozen=True, slots=True)
class PolicyLine:
    # Identifies the line in reasons, e.g. its position or quote line id
    line_ref: str
    product: ProductFacts
    offer: LineOffer
    substitutes_for: SubstitutedProduct | None = None


@dataclass(frozen=True, slots=True)
class PolicyInput:
    mandate: MandateTerms
    lines: tuple[PolicyLine, ...]
    deliver_by: date
    # What the agent's orders committed in the current spend period, before this quote
    period_spend: Decimal
    # The same per category code; a category without an entry has spent nothing
    category_period_spend: Mapping[str, Decimal] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PolicyReason:
    code: PolicyReasonCode
    severity: Severity
    # None for a quote-wide rule
    line_ref: str | None
    # One plain-English sentence for approvers
    message: str
    # The numbers behind the reason, camelCase keys, e.g. {"orderTotal": ..., "limit": ...}
    facts: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class LineOutcome:
    line_ref: str
    outcome: PolicyOutcome


@dataclass(frozen=True, slots=True)
class PolicyJudgement:
    # The most severe outcome of any line or quote-wide rule
    outcome: PolicyOutcome
    # Lines in input order, then quote-wide rules
    reasons: tuple[PolicyReason, ...]
    lines: tuple[LineOutcome, ...]
    # Net EUR of the lines that have a total
    quote_total: Decimal
