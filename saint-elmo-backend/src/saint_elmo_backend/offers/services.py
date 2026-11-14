"""
Live offers: price and availability from the Valio Aimo API for a shortlist of
products on a delivery date, with quantities converted to sales units.

The Valio Aimo client hands over the API's values as they are. Turning them into
meaning happens here: `999999` becomes an unknown amount, `error: true` and products the
API left out become `NO_PRICE`, empty schedule lines become `NOT_DELIVERABLE`. An offer
judges nothing; the reason codes only state shortfalls and data gaps for the policy.
"""

from collections.abc import Sequence
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from saint_elmo_backend.accounts import crud as account_crud
from saint_elmo_backend.catalog import crud as catalog_crud
from saint_elmo_backend.catalog.enums import Language
from saint_elmo_backend.catalog.models import Product
from saint_elmo_backend.catalog.services import product_name
from saint_elmo_backend.offers.cache import Cached, OfferCache
from saint_elmo_backend.offers.dtos import (
    Money,
    OfferAvailability,
    OfferLine,
    OfferPrice,
    OfferProvenance,
    OfferQuantity,
    Offers,
    RequestedProduct,
)
from saint_elmo_backend.offers.enums import LogisticModel, OfferReasonCode
from saint_elmo_backend.offers.exceptions import CustomerNumberMissingError, UnknownProductsError
from saint_elmo_backend.offers.quantity import (
    PackagingMeasure,
    PriceComparison,
    ProductMeasures,
    convert_quantity,
)
from saint_elmo_backend.offers.timestamps import parse_date, parse_timestamp
from saint_elmo_backend.valio_aimo.client import ValioAimoClient
from saint_elmo_backend.valio_aimo.schemas import ProductAvailability, ProductPrice

OFFER_SOURCE = "Valio Aimo price and availability API"

# The API's placeholder for an amount it doesn't know (TERMINAL products)
UNKNOWN_AMOUNT = Decimal("999999")
_CENT = Decimal("0.01")


async def get_offers(
    session: AsyncSession,
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    *,
    organization_id: int,
    deliver_by: date,
    requested: Sequence[RequestedProduct],
    language: Language,
    now: datetime,
    ignore_closing_time: bool = False,
    use_cache: bool = True,
) -> Offers:
    """
    Raises `UnknownProductsError` listing every unknown code, `CustomerNumberMissingError`,
    and lets the client's `ValioAimoError` through when the API stays unavailable.

    `use_cache=False` asks the API for every product, as placing an order must; the
    fresh answers still refresh the cache.

    `ignore_closing_time` is a demo setting for the live mock, whose closing times are a
    frozen snapshot that has passed: a passed closing time then neither misses the
    deadline nor limits `validUntil`. It is still reported.
    """
    codes = list(dict.fromkeys(product_request.product_code for product_request in requested))
    products = {p.code: p for p in await catalog_crud.get_products_by_codes(session, codes)}
    if unknown := [code for code in codes if code not in products]:
        raise UnknownProductsError(unknown)

    # Never from the request: the customer is the caller's own buyer organisation
    customer = await account_crud.get_customer_number(session, organization_id)
    if not customer:
        raise CustomerNumberMissingError(organization_id)

    prices = await _prices(valio_aimo, cache, customer, deliver_by, codes, now, use_cache)
    availability = await _availability(
        valio_aimo, cache, customer, deliver_by, codes, now, use_cache
    )

    return Offers(
        deliver_by=deliver_by,
        evaluated_at=now,
        lines=[
            _offer_line(
                product_request,
                products[product_request.product_code],
                prices.get(product_request.product_code),
                availability.get(product_request.product_code),
                deliver_by=deliver_by,
                language=language,
                now=now,
                ignore_closing_time=ignore_closing_time,
            )
            for product_request in requested
        ],
    )


async def _prices(
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    customer: str,
    on: date,
    codes: list[str],
    now: datetime,
    use_cache: bool,
) -> dict[str, tuple[Cached[ProductPrice], bool]]:
    """
    Product code -> (price, whether it came from the cache). Only uncached products are
    sent to the API.
    """
    found = {
        code: entry
        for code in codes
        if use_cache and (entry := cache.get_price(customer, code, on, now))
    }
    result = {code: (entry, True) for code, entry in found.items()}

    if missing := [code for code in codes if code not in found]:
        for code, price in (await valio_aimo.price(customer, on, missing)).items():
            cache.put_price(customer, code, on, price, now)
            result[code] = (Cached(price, now, now), False)
    return result


async def _availability(
    valio_aimo: ValioAimoClient,
    cache: OfferCache,
    customer: str,
    on: date,
    codes: list[str],
    now: datetime,
    use_cache: bool,
) -> dict[str, tuple[Cached[ProductAvailability], bool]]:
    found = {
        code: entry
        for code in codes
        if use_cache and (entry := cache.get_availability(customer, code, on, now))
    }
    result = {code: (entry, True) for code, entry in found.items()}

    if missing := [code for code in codes if code not in found]:
        for code, availability in (await valio_aimo.availability(customer, on, missing)).items():
            cache.put_availability(customer, code, on, availability, now)
            result[code] = (Cached(availability, now, now), False)
    return result


def _offer_line(
    product_request: RequestedProduct,
    product: Product,
    price_entry: tuple[Cached[ProductPrice], bool] | None,
    availability_entry: tuple[Cached[ProductAvailability], bool] | None,
    *,
    deliver_by: date,
    language: Language,
    now: datetime,
    ignore_closing_time: bool,
) -> OfferLine:
    reasons: list[OfferReasonCode] = []

    price = _offer_price(price_entry[0].value) if price_entry else None
    if price is None:
        reasons.append(OfferReasonCode.NO_PRICE)

    availability = None
    if availability_entry is not None:
        availability, availability_reasons = _offer_availability(
            availability_entry[0].value,
            product,
            deliver_by=deliver_by,
            now=now,
            ignore_closing_time=ignore_closing_time,
        )
        reasons += availability_reasons
    else:
        # The API left the product out of its answer: it can't be delivered on any date
        reasons.append(OfferReasonCode.NOT_DELIVERABLE)

    quantity = None
    if product_request.quantity is not None:
        quantity = _offer_quantity(product_request, product, price, availability)
        reasons += quantity.converted.reason_codes
        if quantity.covered_by_availability is False:
            reasons.append(OfferReasonCode.PARTIAL_AVAILABILITY)

    return OfferLine(
        product=product,
        name=product_name(product, language),
        price=price,
        availability=availability,
        quantity=quantity,
        reason_codes=tuple(dict.fromkeys(reasons)),
        provenance=_provenance(
            price_entry, availability_entry, price, availability, now, ignore_closing_time
        ),
    )


def _offer_price(price: ProductPrice) -> OfferPrice | None:
    catalog = price.catalog_price
    if price.error or catalog is None:
        return None

    comparison = price.comparison_price
    return OfferPrice(
        per_sales_unit=Money(net=catalog.value, gross=catalog.value_with_tax),
        tax_rate=price.tax.tax_rate if price.tax else None,
        currency=catalog.currency,
        comparison_value=comparison.value if comparison and price.comparison_unit else None,
        comparison_unit=price.comparison_unit if comparison else None,
        customer_specific=price.net_price_found,
        valid_from=parse_timestamp(catalog.valid_from),
        valid_to=parse_timestamp(catalog.valid_to),
    )


def _offer_availability(
    availability: ProductAvailability,
    product: Product,
    *,
    deliver_by: date,
    now: datetime,
    ignore_closing_time: bool,
) -> tuple[OfferAvailability, list[OfferReasonCode]]:
    reasons: list[OfferReasonCode] = []
    logistic_model = _logistic_model(availability.logistic_model)
    closing_time = parse_timestamp(availability.closing_time)
    closing_passed = not ignore_closing_time and closing_time is not None and closing_time <= now

    lines = sorted(
        availability.schedule_lines,
        key=lambda line: parse_date(line.available_date) or date.max,
    )
    # The earliest schedule line is the soonest the product can arrive
    earliest = parse_date(lines[0].available_date) if lines else None
    # Stock is what's available by deliverBy: the last line on or before it. When every
    # line is late, the earliest one is the best the API offers.
    on_time = [line for line in lines if (d := parse_date(line.available_date)) and d <= deliver_by]
    line = on_time[-1] if on_time else (lines[0] if lines else None)
    sales_blocked = availability.sales_block or bool(line and line.sales_block)

    amount = None
    if (
        line is not None
        and logistic_model is not LogisticModel.TERMINAL
        and line.available_amount != UNKNOWN_AMOUNT
        and line.sales_unit.upper() == product.sales_unit.upper()
    ):
        amount = line.available_amount

    if earliest is None:
        reasons.append(OfferReasonCode.NOT_DELIVERABLE)
    elif earliest > deliver_by:
        reasons.append(OfferReasonCode.LATE_DELIVERY)
    if sales_blocked:
        reasons.append(OfferReasonCode.SALES_BLOCKED)
    if closing_passed:
        reasons.append(OfferReasonCode.CLOSING_TIME_PASSED)

    return (
        OfferAvailability(
            logistic_model=logistic_model,
            available_amount=amount,
            earliest_date=earliest,
            closing_time=closing_time,
            sales_blocked=sales_blocked,
            meets_deadline=earliest is not None and earliest <= deliver_by and not closing_passed,
        ),
        reasons,
    )


def _offer_quantity(
    product_request: RequestedProduct,
    product: Product,
    price: OfferPrice | None,
    availability: OfferAvailability | None,
) -> OfferQuantity:
    assert product_request.quantity is not None
    comparison = (
        PriceComparison(
            catalog_price=price.per_sales_unit.net,
            comparison_price=price.comparison_value,
            comparison_unit=price.comparison_unit,
        )
        if price is not None and price.comparison_value is not None
        else None
    )
    converted = convert_quantity(
        product_request.quantity, product_request.unit, product_measures(product), comparison
    )

    sales_units = converted.sales_units
    line_total = None
    if price is not None and sales_units is not None:
        line_total = Money(
            net=_to_cents(sales_units * price.per_sales_unit.net),
            gross=_to_cents(sales_units * price.per_sales_unit.gross),
        )

    covered = None
    if sales_units is not None and availability and availability.available_amount is not None:
        covered = availability.available_amount >= sales_units

    return OfferQuantity(
        converted=converted, line_total=line_total, covered_by_availability=covered
    )


def product_measures(product: Product) -> ProductMeasures:
    """
    The catalog facts Quantity conversion needs. Load units, packaging levels and
    translations first.
    """
    return ProductMeasures(
        sales_unit=product.sales_unit,
        lot_size=product.allowed_lot_size,
        unit_sizes={unit.unit_code: unit.size_in_base_units for unit in product.units},
        name=product_name(product, Language.EN),
        packaging=[
            PackagingMeasure(
                level=level.level,
                net_weight_g=level.net_weight_g,
                volume_value=level.volume_value,
                volume_unit=level.volume_unit,
            )
            for level in product.packaging_levels
        ],
    )


def _provenance(
    price_entry: tuple[Cached[ProductPrice], bool] | None,
    availability_entry: tuple[Cached[ProductAvailability], bool] | None,
    price: OfferPrice | None,
    availability: OfferAvailability | None,
    now: datetime,
    ignore_closing_time: bool,
) -> OfferProvenance:
    entries = [e for e in (price_entry, availability_entry) if e is not None]
    deadlines = [
        d
        for d in (
            price.valid_to if price else None,
            _closing_deadline(availability, now, ignore_closing_time),
        )
        if d is not None
    ]
    return OfferProvenance(
        source=OFFER_SOURCE,
        fetched_at=min((entry.fetched_at for entry, _ in entries), default=now),
        valid_until=min(deadlines, default=None),
        cached=any(cached for _, cached in entries),
    )


def _closing_deadline(
    availability: OfferAvailability | None, now: datetime, ignore_closing_time: bool
) -> datetime | None:
    if availability is None or availability.closing_time is None:
        return None
    if ignore_closing_time and availability.closing_time <= now:
        return None
    return availability.closing_time


def _logistic_model(value: str | None) -> LogisticModel | None:
    # The API sends title case (`Stock`, `Terminal`)
    try:
        return LogisticModel(value.upper()) if value else None
    except ValueError:
        return None


def _to_cents(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)
