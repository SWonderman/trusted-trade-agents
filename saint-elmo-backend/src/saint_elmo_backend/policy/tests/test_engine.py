"""
The policy engine: a basket of priced lines judged against a mandate. Pure, so no
database or API.
"""

import json
from dataclasses import asdict, fields, replace
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from saint_elmo_backend.catalog.dtos import ClaimCode
from saint_elmo_backend.catalog.enums import AllergenContainment, AllergenStrictness
from saint_elmo_backend.mandates.dtos import CategorySpendCap, MandateTerms
from saint_elmo_backend.mandates.enums import SpendPeriod, SubstitutionPolicy
from saint_elmo_backend.offers.enums import ConversionBasis, CrossCheck, LogisticModel
from saint_elmo_backend.offers.quantity import Conversion, ConvertedQuantity
from saint_elmo_backend.policy.dtos import (
    LineOffer,
    LineOutcome,
    PolicyInput,
    PolicyLine,
    ProductFacts,
    SubstitutedProduct,
)
from saint_elmo_backend.policy.engine import evaluate
from saint_elmo_backend.policy.enums import PolicyOutcome, PolicyReasonCode, Severity

DELIVER_BY = date(2026, 11, 16)

MANDATE = MandateTerms(
    max_order_total=Decimal("2000"),
    period_spend_cap=Decimal("5000"),
    spend_period=SpendPeriod.WEEK,
    auto_approve_up_to=Decimal("1000"),
    substitution_policy=SubstitutionPolicy.IF_REQUIREMENTS_HOLD,
    max_substitute_price_increase_pct=Decimal("10"),
)

MILK = ProductFacts(
    category_code="10400",
    vendor="Valio Oy",
    country_of_origin="fi",
    delivery_reliability=Decimal("0.98"),
)


def _offer(**changes) -> LineOffer:
    """
    10 KI at 31.31 €, in stock, on time.
    """
    offer = LineOffer(
        unit_price=Decimal("31.31"),
        sales_blocked=False,
        earliest_date=date(2026, 11, 16),
        closing_time=datetime(2026, 11, 15, 10, tzinfo=UTC),
        closing_time_passed=False,
        logistic_model=LogisticModel.STOCK,
        available_amount=Decimal("500"),
        quantity=ConvertedQuantity(
            requested_value=Decimal("10"),
            requested_unit="KI",
            lot_size=Decimal("1"),
            sales_units=Decimal("10"),
            rounded_up=False,
            delivered_value=Decimal("10"),
            delivered_unit="KI",
        ),
        line_total=Decimal("313.10"),
    )
    return replace(offer, **changes)


def _line(line_ref: str = "1", *, product: ProductFacts = MILK, **offer_changes) -> PolicyLine:
    return PolicyLine(line_ref=line_ref, product=product, offer=_offer(**offer_changes))


def _input(*lines: PolicyLine, mandate: MandateTerms = MANDATE, **changes) -> PolicyInput:
    policy_input = PolicyInput(
        mandate=mandate,
        lines=lines or (_line(),),
        deliver_by=DELIVER_BY,
        period_spend=Decimal("0"),
    )
    return replace(policy_input, **changes)


def test_a_compliant_quote_under_the_auto_approve_limit_is_auto_approved():
    judgement = evaluate(_input())

    assert judgement.outcome is PolicyOutcome.AUTO_APPROVE
    assert judgement.reasons == ()
    assert judgement.quote_total == Decimal("313.10")


UNCONVERTED = ConvertedQuantity(
    requested_value=Decimal("1000"), requested_unit="L", lot_size=Decimal("1")
)
# 200 L at 20 L per KI by the price ratio, which nothing could confirm
UNCERTAIN = ConvertedQuantity(
    requested_value=Decimal("200"),
    requested_unit="L",
    lot_size=Decimal("1"),
    conversion=Conversion(
        per_sales_unit=Decimal("20"),
        unit="L",
        basis=ConversionBasis.PRICE_COMPARISON,
        cross_check=CrossCheck.UNCHECKED,
    ),
    sales_units=Decimal("10"),
    rounded_up=False,
    delivered_value=Decimal("200"),
    delivered_unit="L",
)
# 9 KI rounded up to a lot size of 5
ROUNDED = ConvertedQuantity(
    requested_value=Decimal("9"),
    requested_unit="KI",
    lot_size=Decimal("5"),
    sales_units=Decimal("10"),
    rounded_up=True,
    delivered_value=Decimal("10"),
    delivered_unit="KI",
)


@pytest.mark.parametrize(
    ("offer_changes", "code", "severity"),
    [
        ({"sales_blocked": True}, PolicyReasonCode.SALES_BLOCKED, Severity.REJECT),
        ({"earliest_date": None}, PolicyReasonCode.NOT_DELIVERABLE, Severity.REJECT),
        ({"unit_price": None, "line_total": None}, PolicyReasonCode.NO_PRICE, Severity.REJECT),
        ({"closing_time_passed": True}, PolicyReasonCode.CLOSING_TIME_PASSED, Severity.REJECT),
        (
            {"quantity": UNCONVERTED, "line_total": None},
            PolicyReasonCode.CONVERSION_UNAVAILABLE,
            Severity.REJECT,
        ),
        (
            {"available_amount": Decimal("6")},
            PolicyReasonCode.PARTIAL_AVAILABILITY,
            Severity.NEEDS_HUMAN,
        ),
        (
            {"earliest_date": date(2026, 11, 18)},
            PolicyReasonCode.LATE_DELIVERY,
            Severity.NEEDS_HUMAN,
        ),
        (
            {"logistic_model": LogisticModel.TERMINAL, "available_amount": None},
            PolicyReasonCode.STOCK_UNKNOWN,
            Severity.INFO,
        ),
        ({"quantity": UNCERTAIN}, PolicyReasonCode.CONVERSION_UNCERTAIN, Severity.INFO),
        ({"quantity": ROUNDED}, PolicyReasonCode.ROUNDED_TO_LOT_SIZE, Severity.INFO),
    ],
)
def test_each_offer_reason_in_isolation(offer_changes, code, severity):
    judgement = evaluate(_input(_line("7", **offer_changes)))

    assert [(r.code, r.severity, r.line_ref) for r in judgement.reasons] == [(code, severity, "7")]
    assert judgement.outcome is severity.outcome
    assert judgement.lines[0].outcome is severity.outcome


# GS1 allergen code for milk
MILK_ALLERGEN = "AM"


@pytest.mark.parametrize(
    ("strictness", "containment", "expected"),
    [
        # CONTAINS is excluded at every strictness
        (
            AllergenStrictness.CONTAINS,
            AllergenContainment.CONTAINS,
            [PolicyReasonCode.CONTAINS_EXCLUDED_ALLERGEN],
        ),
        (
            AllergenStrictness.MAY_CONTAIN,
            AllergenContainment.CONTAINS,
            [PolicyReasonCode.CONTAINS_EXCLUDED_ALLERGEN],
        ),
        (
            AllergenStrictness.DECLARED_FREE,
            AllergenContainment.CONTAINS,
            [PolicyReasonCode.CONTAINS_EXCLUDED_ALLERGEN],
        ),
        # MAY_CONTAIN only from strictness may_contain on
        (AllergenStrictness.CONTAINS, AllergenContainment.MAY_CONTAIN, []),
        (
            AllergenStrictness.MAY_CONTAIN,
            AllergenContainment.MAY_CONTAIN,
            [PolicyReasonCode.MAY_CONTAIN_EXCLUDED_ALLERGEN],
        ),
        (
            AllergenStrictness.DECLARED_FREE,
            AllergenContainment.MAY_CONTAIN,
            [PolicyReasonCode.MAY_CONTAIN_EXCLUDED_ALLERGEN],
        ),
        # declared_free accepts only a FREE_FROM row
        (
            AllergenStrictness.DECLARED_FREE,
            AllergenContainment.UNDECLARED,
            [PolicyReasonCode.ALLERGEN_NOT_DECLARED_FREE],
        ),
        (AllergenStrictness.DECLARED_FREE, None, [PolicyReasonCode.ALLERGEN_NOT_DECLARED_FREE]),
        (AllergenStrictness.DECLARED_FREE, AllergenContainment.FREE_FROM, []),
        (AllergenStrictness.MAY_CONTAIN, AllergenContainment.FREE_FROM, []),
    ],
)
def test_excluded_allergens_by_strictness(strictness, containment, expected):
    allergens = {} if containment is None else {MILK_ALLERGEN: containment}
    product = replace(MILK, allergens=allergens)
    mandate = replace(MANDATE, excluded_allergens=(MILK_ALLERGEN,), allergen_strictness=strictness)

    judgement = evaluate(_input(_line(product=product), mandate=mandate))

    assert [r.code for r in judgement.reasons] == expected
    assert all(r.severity is Severity.REJECT for r in judgement.reasons)
    assert all(r.facts["allergen"] == MILK_ALLERGEN for r in judgement.reasons)


def test_unknown_allergen_data_is_never_declared_free():
    mandate = replace(
        MANDATE,
        excluded_allergens=(MILK_ALLERGEN, "AW"),
        allergen_strictness=AllergenStrictness.DECLARED_FREE,
    )
    product = replace(MILK, allergens={"AW": AllergenContainment.FREE_FROM})

    judgement = evaluate(_input(_line(product=product), mandate=mandate))

    assert judgement.outcome is PolicyOutcome.REJECT
    [reason] = judgement.reasons
    assert reason.code is PolicyReasonCode.ALLERGEN_NOT_DECLARED_FREE
    assert reason.facts == {"allergen": MILK_ALLERGEN, "declared": "UNKNOWN"}


LACTOSE_FREE = ClaimCode(type="FREE_FROM", element="LACTOSE")


@pytest.mark.parametrize(
    ("mandate_changes", "product_changes", "code", "severity"),
    [
        # Block-lists
        (
            {"blocked_category_codes": ("10400",)},
            {},
            PolicyReasonCode.BLOCKED_CATEGORY,
            Severity.REJECT,
        ),
        ({"blocked_vendors": ("Valio Oy",)}, {}, PolicyReasonCode.BLOCKED_VENDOR, Severity.REJECT),
        # Allow-lists
        (
            {"allowed_category_codes": ("10500",)},
            {},
            PolicyReasonCode.CATEGORY_NOT_ALLOWED,
            Severity.NEEDS_HUMAN,
        ),
        (
            {"allowed_vendors": ("Arla Oy",)},
            {},
            PolicyReasonCode.VENDOR_NOT_ALLOWED,
            Severity.NEEDS_HUMAN,
        ),
        (
            {"allowed_countries_of_origin": ("se",)},
            {},
            PolicyReasonCode.ORIGIN_NOT_ALLOWED,
            Severity.NEEDS_HUMAN,
        ),
        # An unknown origin isn't on any allow-list
        (
            {"allowed_countries_of_origin": ("fi",)},
            {"country_of_origin": None},
            PolicyReasonCode.ORIGIN_NOT_ALLOWED,
            Severity.NEEDS_HUMAN,
        ),
        # Requirements; not declared counts as missing
        (
            {"required_claims": (LACTOSE_FREE,)},
            {},
            PolicyReasonCode.MISSING_REQUIRED_CLAIM,
            Severity.NEEDS_HUMAN,
        ),
        (
            {"required_labels": ("EU_ORGANIC_FARMING",)},
            {},
            PolicyReasonCode.MISSING_REQUIRED_LABEL,
            Severity.NEEDS_HUMAN,
        ),
        (
            {"required_diets": ("VEGAN",)},
            {},
            PolicyReasonCode.MISSING_REQUIRED_DIET,
            Severity.NEEDS_HUMAN,
        ),
        # Reliability below the minimum
        (
            {"min_delivery_reliability": Decimal("0.99")},
            {},
            PolicyReasonCode.BELOW_MIN_RELIABILITY,
            Severity.NEEDS_HUMAN,
        ),
    ],
)
def test_each_mandate_reason_in_isolation(mandate_changes, product_changes, code, severity):
    mandate = replace(MANDATE, **mandate_changes)
    product = replace(MILK, **product_changes)

    judgement = evaluate(_input(_line("3", product=product), mandate=mandate))

    assert [(r.code, r.severity, r.line_ref) for r in judgement.reasons] == [(code, severity, "3")]
    assert judgement.outcome is severity.outcome


@pytest.mark.parametrize(
    ("mandate_changes", "product_changes"),
    [
        ({"allowed_category_codes": ("10400", "10500")}, {}),
        ({"allowed_vendors": ("Valio Oy",)}, {}),
        ({"allowed_countries_of_origin": ("fi", "se")}, {}),
        ({"required_claims": (LACTOSE_FREE,)}, {"claims": (LACTOSE_FREE,)}),
        ({"required_labels": ("EU_ORGANIC_FARMING",)}, {"labels": ("EU_ORGANIC_FARMING",)}),
        ({"required_diets": ("VEGAN",)}, {"diets": ("VEGAN", "HALAL")}),
        ({"min_delivery_reliability": Decimal("0.98")}, {}),
        # No reliability data doesn't trigger the minimum
        ({"min_delivery_reliability": Decimal("0.99")}, {"delivery_reliability": None}),
    ],
)
def test_a_product_within_the_mandate_raises_nothing(mandate_changes, product_changes):
    mandate = replace(MANDATE, **mandate_changes)
    product = replace(MILK, **product_changes)

    judgement = evaluate(_input(_line(product=product), mandate=mandate))

    assert judgement.reasons == ()


def test_a_claim_on_another_element_is_not_the_required_claim():
    mandate = replace(MANDATE, required_claims=(LACTOSE_FREE,))
    product = replace(MILK, claims=(ClaimCode(type="FREE_FROM", element="GLUTEN"),))

    judgement = evaluate(_input(_line(product=product), mandate=mandate))

    [reason] = judgement.reasons
    assert reason.code is PolicyReasonCode.MISSING_REQUIRED_CLAIM
    assert reason.facts == {"claim": "FREE_FROM_LACTOSE"}


def test_late_delivery_is_only_info_when_the_mandate_accepts_later_dates():
    mandate = replace(MANDATE, later_delivery_needs_approval=False)

    judgement = evaluate(_input(_line(earliest_date=date(2026, 11, 18)), mandate=mandate))

    assert judgement.outcome is PolicyOutcome.AUTO_APPROVE
    [reason] = judgement.reasons
    assert (reason.code, reason.severity) == (PolicyReasonCode.LATE_DELIVERY, Severity.INFO)
    assert reason.facts == {"earliestDate": date(2026, 11, 18), "deliverBy": DELIVER_BY}


def test_enough_known_stock_is_not_a_shortfall():
    judgement = evaluate(_input(_line(available_amount=Decimal("10"))))

    assert judgement.reasons == ()


def _litres(litres_per_ki: str) -> ConvertedQuantity:
    """
    200 L in a product holding `litres_per_ki` per KI.
    """
    per_sales_unit = Decimal(litres_per_ki)
    return ConvertedQuantity(
        requested_value=Decimal("200"),
        requested_unit="L",
        lot_size=Decimal("1"),
        conversion=Conversion(
            per_sales_unit=per_sales_unit,
            unit="L",
            basis=ConversionBasis.PRICE_COMPARISON,
            cross_check=CrossCheck.AGREES,
        ),
        sales_units=Decimal("200") / per_sales_unit,
        rounded_up=False,
        delivered_value=Decimal("200"),
        delivered_unit="L",
    )


# The original: 20 L per KI at 30.00 € = 1.50 € per litre
ORIGINAL = SubstitutedProduct(
    product_code="463038",
    offer=_offer(unit_price=Decimal("30.00"), quantity=_litres("20"), line_total=Decimal("300")),
)
OAT_DRINK = replace(MILK, vendor="Oatly AB")


def _substitute(unit_price: str, litres_per_ki: str = "20", original=ORIGINAL) -> PolicyLine:
    return PolicyLine(
        line_ref="2",
        product=OAT_DRINK,
        offer=_offer(unit_price=Decimal(unit_price), quantity=_litres(litres_per_ki)),
        substitutes_for=original,
    )


@pytest.mark.parametrize(
    ("substitution_policy", "expected"),
    [
        (SubstitutionPolicy.NEVER, [(PolicyReasonCode.SUBSTITUTION_NOT_ALLOWED, Severity.REJECT)]),
        (
            SubstitutionPolicy.ALWAYS_NEEDS_APPROVAL,
            [(PolicyReasonCode.SUBSTITUTE_NEEDS_APPROVAL, Severity.NEEDS_HUMAN)],
        ),
        (SubstitutionPolicy.IF_REQUIREMENTS_HOLD, []),
    ],
)
def test_substitution_policy(substitution_policy, expected):
    mandate = replace(MANDATE, substitution_policy=substitution_policy)

    judgement = evaluate(_input(_substitute("30.00"), mandate=mandate))

    assert [(r.code, r.severity) for r in judgement.reasons] == expected


def test_a_substitute_dearer_per_buyer_unit_than_allowed_needs_a_human():
    # 34.50 € for 20 L = 1.725 € per litre, 15 % over the original's 1.50
    judgement = evaluate(_input(_substitute("34.50")))

    assert judgement.outcome is PolicyOutcome.NEEDS_HUMAN
    [reason] = judgement.reasons
    assert (reason.code, reason.severity, reason.line_ref) == (
        PolicyReasonCode.SUBSTITUTE_PRICE_INCREASE,
        Severity.NEEDS_HUMAN,
        "2",
    )
    assert reason.facts == {
        "originalProductCode": "463038",
        "comparable": True,
        "buyerUnit": "L",
        "originalPricePerBuyerUnit": Decimal("1.5"),
        "pricePerBuyerUnit": Decimal("1.725"),
        "increasePct": Decimal("15.00"),
        "maxIncreasePct": Decimal("10"),
    }


def test_a_price_increase_of_exactly_the_maximum_is_allowed():
    # 33.00 € for 20 L = 1.65 € per litre, 10 % over
    assert evaluate(_input(_substitute("33.00"))).reasons == ()


def test_substitute_prices_compare_per_buyer_unit_not_per_sales_unit():
    # Dearer per KI, but 36.00 € for 24 L = 1.50 € per litre, the same as the original
    assert evaluate(_input(_substitute("36.00", litres_per_ki="24"))).reasons == ()


@pytest.mark.parametrize(
    "original",
    [
        # The original's price is unknown
        replace(ORIGINAL, offer=replace(ORIGINAL.offer, unit_price=None, line_total=None)),
        # The original was asked for in another unit
        replace(ORIGINAL, offer=_offer(unit_price=Decimal("30.00"))),
    ],
)
def test_a_substitute_whose_price_cant_be_compared_needs_a_human(original):
    judgement = evaluate(_input(_substitute("30.00", original=original)))

    [reason] = judgement.reasons
    assert (reason.code, reason.severity) == (
        PolicyReasonCode.SUBSTITUTE_PRICE_INCREASE,
        Severity.NEEDS_HUMAN,
    )
    assert reason.facts["comparable"] is False


def _priced(line_ref: str, total: str, product: ProductFacts = MILK) -> PolicyLine:
    return _line(line_ref, product=product, line_total=Decimal(total))


@pytest.mark.parametrize(
    ("totals", "expected"),
    [
        # At most autoApproveUpTo: nothing to say
        (("600", "400"), []),
        (("600", "600"), [(PolicyReasonCode.OVER_AUTO_APPROVE_LIMIT, Severity.NEEDS_HUMAN)]),
        (("1000", "1000"), [(PolicyReasonCode.OVER_AUTO_APPROVE_LIMIT, Severity.NEEDS_HUMAN)]),
        # Over maxOrderTotal rejects, and isn't also over the auto-approve limit
        (("1000", "1140"), [(PolicyReasonCode.OVER_ORDER_LIMIT, Severity.REJECT)]),
    ],
)
def test_order_total_limits(totals, expected):
    lines = [_priced(str(i), total) for i, total in enumerate(totals)]

    judgement = evaluate(_input(*lines))

    assert [(r.code, r.severity, r.line_ref) for r in judgement.reasons] == [
        (code, severity, None) for code, severity in expected
    ]


def test_over_order_limit_states_the_total_and_the_limit():
    judgement = evaluate(_input(_priced("1", "1000"), _priced("2", "1140")))

    [reason] = judgement.reasons
    assert reason.facts == {"orderTotal": Decimal("2140"), "limit": Decimal("2000")}
    assert judgement.quote_total == Decimal("2140")


def test_period_spend_plus_the_basket_over_the_cap_needs_a_human():
    judgement = evaluate(_input(_priced("1", "600"), period_spend=Decimal("4500")))

    assert judgement.outcome is PolicyOutcome.NEEDS_HUMAN
    [reason] = judgement.reasons
    assert (reason.code, reason.line_ref) == (PolicyReasonCode.OVER_PERIOD_CAP, None)
    assert reason.facts == {
        "periodSpend": Decimal("4500"),
        "orderTotal": Decimal("600"),
        "cap": Decimal("5000"),
    }


def test_reaching_the_period_cap_exactly_is_allowed():
    assert evaluate(_input(_priced("1", "500"), period_spend=Decimal("4500"))).reasons == ()


BUTTER = replace(MILK, category_code="10500")


def test_category_spend_over_its_cap_needs_a_human():
    mandate = replace(
        MANDATE,
        category_spend_caps=(
            CategorySpendCap(category_code="10400", cap=Decimal("800")),
            CategorySpendCap(category_code="10500", cap=Decimal("800")),
        ),
    )
    lines = (_priced("1", "200"), _priced("2", "150"), _priced("3", "500", product=BUTTER))

    judgement = evaluate(
        _input(*lines, mandate=mandate, category_period_spend={"10400": Decimal("500")})
    )

    [reason] = judgement.reasons
    assert (reason.code, reason.severity, reason.line_ref) == (
        PolicyReasonCode.OVER_CATEGORY_CAP,
        Severity.NEEDS_HUMAN,
        None,
    )
    assert reason.facts == {
        "categoryCode": "10400",
        "periodSpend": Decimal("500"),
        "orderTotal": Decimal("350"),
        "cap": Decimal("800"),
    }


def test_splitting_an_order_over_the_period_cap_into_small_quotes_still_hits_the_cap():
    mandate = replace(MANDATE, period_spend_cap=Decimal("2500"))
    period_spend = Decimal("0")
    outcomes = []
    for _ in range(3):
        judgement = evaluate(
            _input(_priced("1", "900"), mandate=mandate, period_spend=period_spend)
        )
        outcomes.append(judgement.outcome)
        period_spend += judgement.quote_total

    assert outcomes == [
        PolicyOutcome.AUTO_APPROVE,
        PolicyOutcome.AUTO_APPROVE,
        PolicyOutcome.NEEDS_HUMAN,
    ]
    assert [r.code for r in judgement.reasons] == [PolicyReasonCode.OVER_PERIOD_CAP]


def test_a_compliant_quote_with_only_info_reasons_is_auto_approved():
    line = _line(quantity=ROUNDED, logistic_model=LogisticModel.TERMINAL, available_amount=None)

    judgement = evaluate(_input(line))

    assert judgement.outcome is PolicyOutcome.AUTO_APPROVE
    assert [r.code for r in judgement.reasons] == [
        PolicyReasonCode.STOCK_UNKNOWN,
        PolicyReasonCode.ROUNDED_TO_LOT_SIZE,
    ]
    assert {r.severity for r in judgement.reasons} == {Severity.INFO}


ORGANIC_MILK = replace(MILK, labels=("EU_ORGANIC_FARMING",))


def test_the_quote_outcome_is_the_most_severe_of_any_line_or_quote_wide_rule():
    mandate = replace(MANDATE, required_labels=("EU_ORGANIC_FARMING",))
    lines = (
        _priced("ok", "300", product=ORGANIC_MILK),
        _priced("unlabelled", "300"),
        _line(
            "blocked",
            sales_blocked=True,
            line_total=Decimal("300"),
            product=ORGANIC_MILK,
        ),
        _line(
            "rounded",
            quantity=ROUNDED,
            line_total=Decimal("300"),
            product=ORGANIC_MILK,
        ),
    )

    judgement = evaluate(_input(*lines, mandate=mandate))

    assert judgement.outcome is PolicyOutcome.REJECT
    assert judgement.lines == (
        LineOutcome("ok", PolicyOutcome.AUTO_APPROVE),
        LineOutcome("unlabelled", PolicyOutcome.NEEDS_HUMAN),
        LineOutcome("blocked", PolicyOutcome.REJECT),
        LineOutcome("rounded", PolicyOutcome.AUTO_APPROVE),
    )
    # Lines in input order, then the quote-wide rules
    assert [(r.line_ref, r.code) for r in judgement.reasons] == [
        ("unlabelled", PolicyReasonCode.MISSING_REQUIRED_LABEL),
        ("blocked", PolicyReasonCode.SALES_BLOCKED),
        ("rounded", PolicyReasonCode.ROUNDED_TO_LOT_SIZE),
        (None, PolicyReasonCode.OVER_AUTO_APPROVE_LIMIT),
    ]


def test_a_quote_wide_rule_alone_decides_the_outcome_when_every_line_is_fine():
    judgement = evaluate(_input(_priced("1", "1500")))

    assert judgement.lines == (LineOutcome("1", PolicyOutcome.AUTO_APPROVE),)
    assert judgement.outcome is PolicyOutcome.NEEDS_HUMAN


def test_one_line_collects_every_reason_that_applies():
    mandate = replace(
        MANDATE,
        blocked_vendors=("Valio Oy",),
        allowed_category_codes=("10500",),
        excluded_allergens=(MILK_ALLERGEN,),
        required_claims=(LACTOSE_FREE,),
    )
    product = replace(MILK, allergens={MILK_ALLERGEN: AllergenContainment.CONTAINS})
    line = _line(
        product=product,
        earliest_date=date(2026, 11, 18),
        available_amount=Decimal("2"),
        quantity=UNCERTAIN,
    )

    judgement = evaluate(_input(line, mandate=mandate))

    assert judgement.outcome is PolicyOutcome.REJECT
    assert [(r.code, r.severity) for r in judgement.reasons] == [
        (PolicyReasonCode.CONTAINS_EXCLUDED_ALLERGEN, Severity.REJECT),
        (PolicyReasonCode.BLOCKED_VENDOR, Severity.REJECT),
        (PolicyReasonCode.CATEGORY_NOT_ALLOWED, Severity.NEEDS_HUMAN),
        (PolicyReasonCode.MISSING_REQUIRED_CLAIM, Severity.NEEDS_HUMAN),
        (PolicyReasonCode.PARTIAL_AVAILABILITY, Severity.NEEDS_HUMAN),
        (PolicyReasonCode.LATE_DELIVERY, Severity.NEEDS_HUMAN),
        (PolicyReasonCode.CONVERSION_UNCERTAIN, Severity.INFO),
    ]


def _busy_input() -> PolicyInput:
    mandate = replace(
        MANDATE,
        excluded_allergens=(MILK_ALLERGEN, "AW"),
        allergen_strictness=AllergenStrictness.DECLARED_FREE,
        required_claims=(LACTOSE_FREE,),
        category_spend_caps=(CategorySpendCap(category_code="10400", cap=Decimal("100")),),
    )
    return _input(
        _line("1", quantity=UNCERTAIN, earliest_date=date(2026, 11, 18)),
        _substitute("34.50"),
        _priced("3", "1900", product=BUTTER),
        mandate=mandate,
        period_spend=Decimal("4000"),
        category_period_spend={"10400": Decimal("50")},
    )


def _serialized(judgement) -> bytes:
    return json.dumps(asdict(judgement), default=str).encode()


def test_identical_inputs_give_byte_identical_outputs():
    first = evaluate(_busy_input())
    second = evaluate(_busy_input())

    # Two separately built inputs, which exercise many rules
    assert first.reasons
    assert _serialized(first) == _serialized(second)


def test_every_message_is_one_plain_sentence():
    for reason in evaluate(_busy_input()).reasons:
        assert reason.message.endswith(".")
        assert "\n" not in reason.message


def test_the_policy_input_has_no_free_text_from_the_agent():
    """
    ADR 0002: the buyer request and the rationale never influence a judgement.
    """
    for dto in (PolicyInput, PolicyLine, ProductFacts, LineOffer, SubstitutedProduct, MandateTerms):
        names = {f.name for f in fields(dto)}
        assert not names & {"buyer_request", "rationale"}, dto


def test_a_category_already_over_its_cap_doesnt_flag_a_quote_without_it():
    mandate = replace(
        MANDATE,
        category_spend_caps=(CategorySpendCap(category_code="10500", cap=Decimal("800")),),
    )

    judgement = evaluate(
        _input(
            _priced("1", "200"), mandate=mandate, category_period_spend={"10500": Decimal("900")}
        )
    )

    assert judgement.reasons == ()
