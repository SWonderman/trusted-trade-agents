from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from saint_elmo_backend.offers.enums import LogisticModel, OfferReasonCode
from saint_elmo_backend.offers.quantity import NormalisedQuantity

if TYPE_CHECKING:
    from saint_elmo_backend.catalog.models import Product


@dataclass(frozen=True, slots=True)
class OfferItem:
    """
    One requested product. `quantity` None asks for price and availability only;
    `unit` None means the quantity is in the product's sales unit.
    """

    product_code: str
    quantity: Decimal | None = None
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class Money:
    net: Decimal
    gross: Decimal


@dataclass(frozen=True, slots=True)
class OfferPrice:
    per_sales_unit: Money
    tax_rate: Decimal | None
    currency: str
    comparison_value: Decimal | None
    comparison_unit: str | None
    customer_specific: bool
    valid_from: datetime | None
    valid_to: datetime | None


@dataclass(frozen=True, slots=True)
class OfferAvailability:
    logistic_model: LogisticModel | None
    # In sales units; None when the API doesn't know it (TERMINAL, 999999)
    available_amount: Decimal | None
    earliest_date: date | None
    closing_time: datetime | None
    sales_blocked: bool
    meets_deadline: bool

    @property
    def available_amount_known(self) -> bool:
        return self.available_amount is not None


@dataclass(frozen=True, slots=True)
class OfferQuantity:
    normalised: NormalisedQuantity
    line_total: Money | None
    # None when the available amount is unknown or the quantity couldn't be converted
    covered_by_availability: bool | None


@dataclass(frozen=True, slots=True)
class OfferProvenance:
    source: str
    # When the oldest part of the offer was fetched from the Valio Aimo API
    fetched_at: datetime
    # The earliest of the price's validTo and the closing time; None if neither is known
    valid_until: datetime | None
    # True when any part of the offer came from the cache
    cached: bool


@dataclass(frozen=True, slots=True)
class OfferLine:
    product: "Product"
    name: str | None
    price: OfferPrice | None
    availability: OfferAvailability | None
    quantity: OfferQuantity | None
    reason_codes: tuple[OfferReasonCode, ...]
    provenance: OfferProvenance


@dataclass(frozen=True, slots=True)
class Offers:
    deliver_by: date
    evaluated_at: datetime
    lines: list[OfferLine]
