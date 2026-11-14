"""
Typed models of the Valio Aimo API (`openapi.json` at the repo root), field for field.

Values come through exactly as the API sends them: `999999` for an unknown TERMINAL
amount, `error: true` on a price, empty `scheduleLines`, `salesBlock`. Dates and times
stay strings because the spec leaves their format open. Interpreting any of it is the
caller's job (#12), not this module's.
"""

from decimal import Decimal

from saint_elmo_backend.core.schema import CamelBaseModel

# Request


class ProductsRequest(CamelBaseModel):
    customer: str
    requested_date: str
    products: list[str]


# Price


class Price(CamelBaseModel):
    value: Decimal
    value_with_tax: Decimal
    valid_from: str
    valid_to: str
    currency: str


class PriceWithTax(CamelBaseModel):
    value: Decimal
    valid_from: str
    valid_to: str
    currency: str


class Tax(CamelBaseModel):
    tax_rate: Decimal
    tax_value: Decimal


class ProductPrice(CamelBaseModel):
    product_id: str
    quantity: Decimal
    catalog_price: Price | None = None
    price_with_tax: PriceWithTax | None = None
    comparison_price: Price | None = None
    comparison_unit: str | None = None
    tax: Tax | None = None
    list_price: Price | None = None
    net_price_found: bool
    error: bool


class PriceResponse(CamelBaseModel):
    customer_id: str
    currency: str
    pricing_date: str
    products: list[ProductPrice]


# Availability


class ScheduleLine(CamelBaseModel):
    sales_block: bool
    available_amount: Decimal
    available_date: str | None = None
    sales_unit: str


class ProductAvailability(CamelBaseModel):
    product_id: str
    closing_time: str | None = None
    sales_block: bool
    logistic_model: str | None = None
    schedule_lines: list[ScheduleLine]


class AvailabilityResponse(CamelBaseModel):
    time_now: str
    requested_date: str
    products: list[ProductAvailability]
