from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import Field, model_validator

from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.catalog.schemas import CarbonFootprint
from saint_elmo_backend.core.schema import CamelBaseModel, DecimalNumber
from saint_elmo_backend.offers.dtos import (
    Money,
    OfferAvailability,
    OfferItem,
    OfferLine,
    OfferPrice,
    OfferProvenance,
    OfferQuantity,
    Offers,
)
from saint_elmo_backend.offers.enums import (
    ConversionBasis,
    CrossCheck,
    LogisticModel,
    OfferReasonCode,
)
from saint_elmo_backend.offers.services import MAX_ITEMS

# Request


class OfferItemRequest(CamelBaseModel):
    product_code: str = Field(min_length=1, max_length=20, examples=["463038"])
    quantity: Decimal | None = Field(
        default=None,
        gt=0,
        description="Optional. With it, the offer converts it to sales units and prices the line",
        examples=[1000],
    )
    unit: str | None = Field(
        default=None,
        min_length=1,
        max_length=10,
        description="`L`, `KG`, or one of the product's unit codes such as `KI` or `ST`. "
        "Without it the quantity is in the product's sales unit",
        examples=["L"],
    )

    @model_validator(mode="after")
    def _unit_needs_quantity(self) -> Self:
        if self.unit is not None and self.quantity is None:
            raise ValueError("unit is only meaningful together with quantity")
        return self

    def to_item(self) -> OfferItem:
        return OfferItem(
            product_code=self.product_code,
            quantity=self.quantity,
            unit=self.unit.upper() if self.unit else None,
        )


class OffersRequest(CamelBaseModel):
    deliver_by: date = Field(
        description="Delivery date, already resolved by the agent (e.g. 'by Monday')"
    )
    items: list[OfferItemRequest] = Field(min_length=1, max_length=MAX_ITEMS)
    language: Language = Field(
        default=Language.EN, description="Language of product names; falls back to fi"
    )


# Response


class MoneyAmount(CamelBaseModel):
    net: DecimalNumber
    gross: DecimalNumber

    @classmethod
    def from_money(cls, money: Money) -> "MoneyAmount":
        return cls(net=money.net, gross=money.gross)


class Measure(CamelBaseModel):
    value: DecimalNumber
    unit: str


class PriceOut(CamelBaseModel):
    per_sales_unit: MoneyAmount
    tax_rate: DecimalNumber | None = Field(description="Percent, e.g. 14.0")
    currency: str
    comparison_price: Measure | None = Field(description="Price per litre or kilogram")
    customer_specific: bool = Field(
        description="A price negotiated for the buyer organisation (`netPriceFound`)"
    )
    valid_from: datetime | None
    valid_to: datetime | None

    @classmethod
    def from_price(cls, price: OfferPrice) -> "PriceOut":
        return cls(
            per_sales_unit=MoneyAmount.from_money(price.per_sales_unit),
            tax_rate=price.tax_rate,
            currency=price.currency,
            comparison_price=(
                Measure(value=price.comparison_value, unit=price.comparison_unit)
                if price.comparison_value is not None and price.comparison_unit
                else None
            ),
            customer_specific=price.customer_specific,
            valid_from=price.valid_from,
            valid_to=price.valid_to,
        )


class AvailabilityOut(CamelBaseModel):
    logistic_model: LogisticModel | None = Field(
        description="STOCK from Valio Aimo's warehouse, TERMINAL via a supplier"
    )
    available_amount: DecimalNumber | None = Field(
        description="In sales units; null when unknown (always for TERMINAL)"
    )
    available_amount_known: bool
    earliest_date: date | None = Field(description="Soonest delivery date; null if none")
    closing_time: datetime | None = Field(description="Order cut-off for the date")
    sales_blocked: bool
    meets_deadline: bool = Field(
        description="Earliest date is on or before deliverBy and the closing time has not passed"
    )

    @classmethod
    def from_availability(cls, availability: OfferAvailability) -> "AvailabilityOut":
        return cls(
            logistic_model=availability.logistic_model,
            available_amount=availability.available_amount,
            available_amount_known=availability.available_amount_known,
            earliest_date=availability.earliest_date,
            closing_time=availability.closing_time,
            sales_blocked=availability.sales_blocked,
            meets_deadline=availability.meets_deadline,
        )


class ConversionOut(CamelBaseModel):
    per_sales_unit: Measure = Field(description="Requested units in one sales unit")
    basis: ConversionBasis = Field(
        description="PRICE_COMPARISON: catalog price / comparison price, for L and KG; "
        "PACKAGING_UNITS: the product's unit sizes"
    )
    cross_check: CrossCheck = Field(
        description="Whether the product name or declared packaging agrees with the amount"
    )


class QuantityOut(CamelBaseModel):
    requested: Measure
    conversion: ConversionOut | None = Field(
        description="Null when the quantity was in sales units or couldn't be converted"
    )
    sales_units: DecimalNumber | None = Field(
        description="Rounded up to whole sales units, then to the lot size; null when the "
        "quantity couldn't be converted"
    )
    lot_size: DecimalNumber
    rounded_up: bool | None
    delivered: Measure | None = Field(description="What the buyer gets, in the requested unit")
    line_total: MoneyAmount | None = Field(description="Null without a price or sales units")
    covered_by_availability: bool | None = Field(
        description="Null when the available amount is unknown"
    )

    @classmethod
    def from_quantity(cls, quantity: OfferQuantity) -> "QuantityOut":
        n = quantity.normalised
        return cls(
            requested=Measure(value=n.requested_value, unit=n.requested_unit),
            conversion=(
                ConversionOut(
                    per_sales_unit=Measure(
                        value=n.conversion.per_sales_unit, unit=n.conversion.unit
                    ),
                    basis=n.conversion.basis,
                    cross_check=n.conversion.cross_check,
                )
                if n.conversion
                else None
            ),
            sales_units=n.sales_units,
            lot_size=n.lot_size,
            rounded_up=n.rounded_up,
            delivered=(
                Measure(value=n.delivered_value, unit=n.delivered_unit)
                if n.delivered_value is not None and n.delivered_unit
                else None
            ),
            line_total=MoneyAmount.from_money(quantity.line_total) if quantity.line_total else None,
            covered_by_availability=quantity.covered_by_availability,
        )


class OfferProvenanceOut(CamelBaseModel):
    source: str
    fetched_at: datetime = Field(description="When the oldest part of the offer was fetched")
    valid_until: datetime | None = Field(
        description="The earliest of the price's validTo and the closing time"
    )
    cached: bool = Field(description="Whether any part of the offer came from the cache")

    @classmethod
    def from_provenance(cls, provenance: OfferProvenance) -> "OfferProvenanceOut":
        return cls(
            source=provenance.source,
            fetched_at=provenance.fetched_at,
            valid_until=provenance.valid_until,
            cached=provenance.cached,
        )


class OfferOut(CamelBaseModel):
    product_code: str
    name: str | None
    sales_unit: str
    price: PriceOut | None = Field(description="Null when the API has no price (NO_PRICE)")
    availability: AvailabilityOut | None = Field(
        description="Null when the API left the product out (NOT_DELIVERABLE)"
    )
    quantity: QuantityOut | None = Field(description="Only when a quantity was given")
    delivery_reliability: DecimalNumber | None = Field(
        description="Share of historical orders delivered as ordered, 0-1"
    )
    carbon_footprint: CarbonFootprint | None
    reason_codes: list[OfferReasonCode]
    provenance: OfferProvenanceOut

    @classmethod
    def from_line(cls, line: OfferLine) -> "OfferOut":
        product = line.product
        return cls(
            product_code=product.code,
            name=line.name,
            sales_unit=product.sales_unit,
            price=PriceOut.from_price(line.price) if line.price else None,
            availability=(
                AvailabilityOut.from_availability(line.availability) if line.availability else None
            ),
            quantity=QuantityOut.from_quantity(line.quantity) if line.quantity else None,
            delivery_reliability=product.delivery_reliability,
            carbon_footprint=(
                CarbonFootprint(value=product.carbon_footprint)
                if product.carbon_footprint is not None
                else None
            ),
            reason_codes=list(line.reason_codes),
            provenance=OfferProvenanceOut.from_provenance(line.provenance),
        )


class OffersResponse(CamelBaseModel):
    deliver_by: date
    evaluated_at: datetime
    items: list[OfferOut] = Field(description="One per requested item, in request order")

    @classmethod
    def from_offers(cls, offers: Offers) -> "OffersResponse":
        return cls(
            deliver_by=offers.deliver_by,
            evaluated_at=offers.evaluated_at,
            items=[OfferOut.from_line(line) for line in offers.lines],
        )
