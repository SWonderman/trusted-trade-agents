"""
The quantity normaliser: a quantity in buyer units or sales units, converted to whole
sales units and the lot size. Pure, so no database or API.
"""

from decimal import Decimal

from saint_elmo_backend.offers.enums import ConversionBasis, CrossCheck, OfferReasonCode
from saint_elmo_backend.offers.quantity import (
    PackagingMeasure,
    PriceComparison,
    ProductMeasures,
    normalise_quantity,
)

# 463038 Valio Eila® 10 l, sold per KI (2 × 10 l). Live: 31.31 € / 1.57 €/L ≈ 20 L per KI
EILA = ProductMeasures(
    sales_unit="KI",
    lot_size=Decimal("1"),
    unit_sizes={"ST": Decimal("1"), "KI": Decimal("2")},
    name="Valio Eila® semi skimmed milk drink 10 l novobox lactose free",
)
EILA_PRICE = PriceComparison(
    catalog_price=Decimal("31.31"), comparison_price=Decimal("1.57"), comparison_unit="L"
)


def test_litres_convert_through_the_comparison_price_and_agree_with_the_name():
    result = normalise_quantity(Decimal("1000"), "L", EILA, EILA_PRICE)

    assert result.conversion is not None
    assert result.conversion.per_sales_unit == Decimal("20")
    assert result.conversion.unit == "L"
    assert result.conversion.basis is ConversionBasis.PRICE_COMPARISON
    assert result.conversion.cross_check is CrossCheck.AGREES
    assert result.sales_units == Decimal("50")
    assert result.rounded_up is False
    assert result.delivered_value == Decimal("1000")
    assert result.delivered_unit == "L"
    assert result.reason_codes == ()


def test_a_quantity_rounds_up_to_whole_sales_units():
    result = normalise_quantity(Decimal("1001"), "L", EILA, EILA_PRICE)

    assert result.sales_units == Decimal("51")
    assert result.rounded_up is True
    assert result.delivered_value == Decimal("1020")
    assert result.delivered_unit == "L"


def test_whole_sales_units_then_round_up_to_the_lot_size():
    # Sold per ST in steps of 6: 7 ST of 1 kg becomes 12
    cheese = ProductMeasures(
        sales_unit="ST",
        lot_size=Decimal("6"),
        unit_sizes={"ST": Decimal("1")},
        name="Edam cheese 1 kg",
    )
    price = PriceComparison(Decimal("9.80"), Decimal("9.80"), "KG")

    result = normalise_quantity(Decimal("6.5"), "KG", cheese, price)

    assert result.sales_units == Decimal("12")
    assert result.lot_size == Decimal("6")
    assert result.rounded_up is True
    assert result.delivered_value == Decimal("12")


def test_a_fractional_lot_size_still_orders_whole_sales_units():
    loose = ProductMeasures(
        sales_unit="KI", lot_size=Decimal("0.01"), unit_sizes={"KI": Decimal("1")}
    )

    result = normalise_quantity(Decimal("2.3"), None, loose, None)

    assert result.sales_units == Decimal("3")
    assert result.rounded_up is True


def test_without_a_unit_the_quantity_is_in_sales_units():
    result = normalise_quantity(Decimal("50"), None, EILA, None)

    assert result.requested_unit == "KI"
    assert result.conversion is None
    assert result.sales_units == Decimal("50")
    assert result.rounded_up is False
    assert result.delivered_value == Decimal("50")
    assert result.delivered_unit == "KI"
    assert result.reason_codes == ()


def test_another_of_the_products_units_converts_by_unit_sizes():
    # 5 ST of a product sold per KI of 2 ST: 3 KI, which delivers 6 ST
    result = normalise_quantity(Decimal("5"), "ST", EILA, None)

    assert result.conversion is not None
    assert result.conversion.per_sales_unit == Decimal("2")
    assert result.conversion.basis is ConversionBasis.PACKAGING_UNITS
    assert result.sales_units == Decimal("3")
    assert result.delivered_value == Decimal("6")
    assert result.delivered_unit == "ST"


def test_a_ratio_the_name_contradicts_is_kept_but_marked_uncertain():
    # The name says 10 l per ST (20 L per KI), the price says 5 L
    price = PriceComparison(Decimal("7.85"), Decimal("1.57"), "L")

    result = normalise_quantity(Decimal("100"), "L", EILA, price)

    assert result.conversion is not None
    assert result.conversion.per_sales_unit == Decimal("5")
    assert result.conversion.cross_check is CrossCheck.DISAGREES
    assert result.sales_units == Decimal("20")
    assert result.reason_codes == (OfferReasonCode.CONVERSION_UNCERTAIN,)


def test_a_ratio_nothing_can_confirm_is_unchecked_and_uncertain():
    nameless = ProductMeasures(
        sales_unit="KI", lot_size=Decimal("1"), unit_sizes={"KI": Decimal("1")}, name="Milk drink"
    )

    result = normalise_quantity(Decimal("1000"), "L", nameless, EILA_PRICE)

    assert result.conversion is not None
    assert result.conversion.per_sales_unit == Decimal("19.943")
    assert result.conversion.cross_check is CrossCheck.UNCHECKED
    assert result.sales_units == Decimal("51")
    assert result.reason_codes == (OfferReasonCode.CONVERSION_UNCERTAIN,)


def test_declared_packaging_can_confirm_the_ratio():
    nameless = ProductMeasures(
        sales_unit="KI",
        lot_size=Decimal("1"),
        unit_sizes={"ST": Decimal("1"), "KI": Decimal("2")},
        name="Milk drink",
        packaging=[PackagingMeasure(level="CASE", volume_value=Decimal("20"), volume_unit="LTR")],
    )

    result = normalise_quantity(Decimal("1000"), "L", nameless, EILA_PRICE)

    assert result.conversion is not None
    assert result.conversion.per_sales_unit == Decimal("20")
    assert result.conversion.cross_check is CrossCheck.AGREES


def test_a_size_in_grams_confirms_a_per_kilogram_price():
    butter = ProductMeasures(
        sales_unit="KI",
        lot_size=Decimal("1"),
        unit_sizes={"ST": Decimal("1"), "KI": Decimal("10")},
        name="Butter 500 g",
    )
    price = PriceComparison(Decimal("42.00"), Decimal("8.40"), "KG")

    result = normalise_quantity(Decimal("20"), "KG", butter, price)

    assert result.conversion is not None
    assert result.conversion.per_sales_unit == Decimal("5")
    assert result.conversion.cross_check is CrossCheck.AGREES
    assert result.sales_units == Decimal("4")


def _assert_unavailable(result):
    assert result.conversion is None
    assert result.sales_units is None
    assert result.rounded_up is None
    assert result.delivered_value is None
    assert result.reason_codes == (OfferReasonCode.CONVERSION_UNAVAILABLE,)


def test_no_price_means_no_buyer_unit_conversion():
    _assert_unavailable(normalise_quantity(Decimal("1000"), "L", EILA, None))


def test_a_comparison_price_in_another_unit_cannot_convert():
    _assert_unavailable(normalise_quantity(Decimal("1000"), "KG", EILA, EILA_PRICE))


def test_a_unit_the_product_does_not_have_cannot_convert():
    result = normalise_quantity(Decimal("3"), "PAL", EILA, EILA_PRICE)

    _assert_unavailable(result)
    assert result.requested_value == Decimal("3")
    assert result.requested_unit == "PAL"
