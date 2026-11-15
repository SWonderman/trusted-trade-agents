"""
Quantity conversion: turns a quantity in buyer units
(L, KG) or in one of the product's units into whole sales units and the lot size.

For L and KG the amount per sales unit comes from the price: catalog price divided by
comparison price (EUR per sales unit / EUR per litre = litres per sales unit). It is
cross-checked against the size in the product name and the declared packaging. When
the cross-check agrees, the packaged amount it agrees with is used: the price ratio
carries cent rounding (31.31 / 1.57 = 19.94 L, for a 2 × 10 l case).
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from saint_elmo_backend.offers.enums import ConversionBasis, CrossCheck, OfferReasonCode

BUYER_UNITS = ("L", "KG")

# A cross-check candidate within this share of the price ratio agrees with it
CROSS_CHECK_TOLERANCE = Decimal("0.05")
# The price ratio is shown to this precision when nothing confirms it
_RATIO_PRECISION = Decimal("0.001")

# Sizes in product names: "10 l", "1,5 kg", "500 g", "2 x 10 l", "6×200 ml"
_NAME_SIZE = re.compile(
    r"(?:(?P<count>\d+)\s*[x×]\s*)?(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>kg|g|l|dl|cl|ml)\b",
    re.IGNORECASE,
)
# Factor to the buyer unit, per unit found in names and packaging data
_TO_BUYER_UNIT: dict[str, tuple[str, Decimal]] = {
    "kg": ("KG", Decimal("1")),
    "kgm": ("KG", Decimal("1")),
    "g": ("KG", Decimal("0.001")),
    "grm": ("KG", Decimal("0.001")),
    "l": ("L", Decimal("1")),
    "ltr": ("L", Decimal("1")),
    "dl": ("L", Decimal("0.1")),
    "dlt": ("L", Decimal("0.1")),
    "cl": ("L", Decimal("0.01")),
    "clt": ("L", Decimal("0.01")),
    "ml": ("L", Decimal("0.001")),
    "mlt": ("L", Decimal("0.001")),
}


@dataclass(frozen=True, slots=True)
class PackagingMeasure:
    """
    One declared packaging level (GS1 `unitConversions`): its net content.
    """

    level: str  # BASE_UNIT_OR_EACH or CASE
    net_weight_g: Decimal | None = None
    volume_value: Decimal | None = None
    volume_unit: str | None = None


@dataclass(frozen=True, slots=True)
class ProductMeasures:
    """
    What the catalog knows about how a product is packed and sold.
    """

    sales_unit: str
    lot_size: Decimal
    # Unit code -> size in base units, e.g. {"ST": 1, "KI": 2}
    unit_sizes: Mapping[str, Decimal]
    name: str | None = None
    packaging: Sequence[PackagingMeasure] = field(default=())


@dataclass(frozen=True, slots=True)
class PriceComparison:
    """
    From the live price: EUR per sales unit and EUR per comparison unit (L or KG).
    """

    catalog_price: Decimal
    comparison_price: Decimal
    comparison_unit: str | None


@dataclass(frozen=True, slots=True)
class Conversion:
    per_sales_unit: Decimal
    unit: str
    basis: ConversionBasis
    cross_check: CrossCheck


@dataclass(frozen=True, slots=True)
class ConvertedQuantity:
    """
    `sales_units`, `rounded_up` and `delivered_*` are None when the quantity could not
    be converted (`CONVERSION_UNAVAILABLE`).
    """

    requested_value: Decimal
    requested_unit: str
    lot_size: Decimal
    conversion: Conversion | None = None
    sales_units: Decimal | None = None
    rounded_up: bool | None = None
    delivered_value: Decimal | None = None
    delivered_unit: str | None = None
    reason_codes: tuple[OfferReasonCode, ...] = ()


def convert_quantity(
    quantity: Decimal,
    unit: str | None,
    product: ProductMeasures,
    price: PriceComparison | None,
) -> ConvertedQuantity:
    """
    `unit` None means the quantity is already in the product's sales unit.
    """
    requested_unit = (unit or product.sales_unit).upper()
    unavailable = ConvertedQuantity(
        requested_value=quantity,
        requested_unit=requested_unit,
        lot_size=product.lot_size,
        reason_codes=(OfferReasonCode.CONVERSION_UNAVAILABLE,),
    )

    conversion = _conversion(requested_unit, product, price)
    if conversion is None and requested_unit != product.sales_unit.upper():
        return unavailable

    # Sales units per requested unit
    per_sales_unit = conversion.per_sales_unit if conversion else Decimal("1")
    exact = quantity / per_sales_unit
    sales_units = _round_up(_round_up(exact, Decimal("1")), product.lot_size)

    reasons = ()
    if conversion is not None and conversion.cross_check is not CrossCheck.AGREES:
        reasons = (OfferReasonCode.CONVERSION_UNCERTAIN,)

    return ConvertedQuantity(
        requested_value=quantity,
        requested_unit=requested_unit,
        lot_size=product.lot_size,
        conversion=conversion,
        sales_units=sales_units,
        rounded_up=sales_units > exact,
        delivered_value=_strip_zeros(sales_units * per_sales_unit),
        delivered_unit=requested_unit,
        reason_codes=reasons,
    )


def may_express(unit: str, product: ProductMeasures) -> bool:
    """
    Whether the catalog suggests a quantity in `unit` can be converted for the product,
    before a live price confirms it: `unit` is its sales unit, another of its units, or
    L or KG with an amount declared in its name or packaging.
    """
    unit = unit.upper()
    sales_unit = product.sales_unit.upper()
    if unit == sales_unit:
        return True
    if unit in BUYER_UNITS:
        return bool(_cross_check_candidates(unit, product))
    units = {code.upper() for code in product.unit_sizes}
    return unit in units and sales_unit in units


def _conversion(
    unit: str, product: ProductMeasures, price: PriceComparison | None
) -> Conversion | None:
    """
    How many `unit`s one sales unit holds, or None when it is the sales unit itself or
    can't be established.
    """
    if unit == product.sales_unit.upper():
        return None

    if unit in BUYER_UNITS:
        return _buyer_unit_conversion(unit, product, price)

    sizes = {code.upper(): size for code, size in product.unit_sizes.items()}
    sales_size = sizes.get(product.sales_unit.upper())
    unit_size = sizes.get(unit)
    if not sales_size or not unit_size:
        return None
    return Conversion(
        per_sales_unit=_strip_zeros(sales_size / unit_size),
        unit=unit,
        basis=ConversionBasis.PACKAGING_UNITS,
        cross_check=CrossCheck.AGREES,
    )


def _buyer_unit_conversion(
    unit: str, product: ProductMeasures, price: PriceComparison | None
) -> Conversion | None:
    if (
        price is None
        or (price.comparison_unit or "").upper() != unit
        or price.comparison_price <= 0
        or price.catalog_price <= 0
    ):
        return None

    ratio = price.catalog_price / price.comparison_price
    candidates = _cross_check_candidates(unit, product)
    agreeing = next(
        (c for c in candidates if abs(c - ratio) <= ratio * CROSS_CHECK_TOLERANCE), None
    )

    if agreeing is not None:
        per_sales_unit, cross_check = agreeing, CrossCheck.AGREES
    else:
        per_sales_unit = ratio.quantize(_RATIO_PRECISION, rounding=ROUND_HALF_UP)
        cross_check = CrossCheck.DISAGREES if candidates else CrossCheck.UNCHECKED

    return Conversion(
        per_sales_unit=_strip_zeros(per_sales_unit),
        unit=unit,
        basis=ConversionBasis.PRICE_COMPARISON,
        cross_check=cross_check,
    )


def _cross_check_candidates(unit: str, product: ProductMeasures) -> list[Decimal]:
    """
    Amounts of `unit` per sales unit that the catalog suggests. A size in the name or on
    the base packaging level may describe one base unit or the whole sales unit, so both
    readings are offered; the case level is per sales unit when that is a case.
    """
    sizes = {code.upper(): size for code, size in product.unit_sizes.items()}
    sales_size = sizes.get(product.sales_unit.upper(), Decimal("1"))

    per_base_or_sales: list[Decimal] = []
    if (amount := _name_amount(unit, product.name)) is not None:
        per_base_or_sales.append(amount)

    per_case: list[Decimal] = []
    for level in product.packaging:
        amount = _packaging_amount(unit, level)
        if amount is None:
            continue
        (per_case if level.level == "CASE" else per_base_or_sales).append(amount)

    candidates = [a * sales_size for a in per_base_or_sales] + per_base_or_sales + per_case
    return list(dict.fromkeys(_strip_zeros(c) for c in candidates if c > 0))


def _name_amount(unit: str, name: str | None) -> Decimal | None:
    for match in _NAME_SIZE.finditer(name or ""):
        buyer_unit, factor = _TO_BUYER_UNIT[match["unit"].lower()]
        if buyer_unit != unit:
            continue
        amount = Decimal(match["amount"].replace(",", ".")) * factor
        return amount * int(match["count"]) if match["count"] else amount
    return None


def _packaging_amount(unit: str, level: PackagingMeasure) -> Decimal | None:
    if unit == "KG" and level.net_weight_g is not None:
        return level.net_weight_g / 1000
    if level.volume_value is not None and level.volume_unit:
        buyer_unit, factor = _TO_BUYER_UNIT.get(level.volume_unit.lower(), (None, None))
        if buyer_unit == unit and factor is not None:
            return level.volume_value * factor
    return None


def _round_up(value: Decimal, step: Decimal) -> Decimal:
    """
    The smallest multiple of `step` that is at least `value`.
    """
    if step <= 0:
        return value
    return _strip_zeros((value / step).to_integral_value(rounding=ROUND_CEILING) * step)


def _strip_zeros(value: Decimal) -> Decimal:
    """
    Drop trailing zeros without switching to an exponent (20.000 -> 20, not 2E+1).
    """
    normalized = value.normalize()
    return (
        normalized.quantize(Decimal("1")) if normalized == normalized.to_integral() else normalized
    )
