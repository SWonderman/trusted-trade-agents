"""
The policy judges the priced lines of a quote or order against an agent's mandate
and gives a policy outcome with reason codes, per line and for the whole quote.

The engine is deterministic - the same input always gives the same judgment, so the audit trail can be
replayed. Reasons come in a fixed order: lines in input order, each line's reasons in
the order of the checks below, then the quote-wide rules.
"""

from collections.abc import Iterable, Iterator, Mapping
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from saint_elmo_backend.catalog.enums import AllergenStatus, AllergenStrictness
from saint_elmo_backend.mandates.dtos import MandateTerms
from saint_elmo_backend.mandates.enums import SubstitutionPolicy
from saint_elmo_backend.offers.enums import CrossCheck, LogisticModel
from saint_elmo_backend.policy.dtos import (
    LineOutcome,
    PolicyInput,
    PolicyJudgement,
    PolicyLine,
    PolicyReason,
    SubstitutedProduct,
)
from saint_elmo_backend.policy.enums import (
    REASON_SEVERITY,
    PolicyOutcome,
    PolicyReasonCode,
    Severity,
)

# Percentages in messages and facts are shown to the cent
_PCT_DISPLAY_STEP = Decimal("0.01")


def evaluate(policy_input: PolicyInput) -> PolicyJudgement:
    reasons: list[PolicyReason] = []
    line_outcomes: list[LineOutcome] = []
    for line in policy_input.lines:
        line_reasons = list(_line_reasons(line, policy_input))
        reasons += line_reasons
        line_outcomes.append(LineOutcome(line.line_ref, _most_severe(line_reasons)))

    quote_total = _total(policy_input.lines)
    reasons += _quote_reasons(policy_input, quote_total)

    return PolicyJudgement(
        outcome=_most_severe(reasons),
        reasons=tuple(reasons),
        lines=tuple(line_outcomes),
        quote_total=quote_total,
    )


def _line_reasons(line: PolicyLine, policy_input: PolicyInput) -> Iterator[PolicyReason]:
    mandate = policy_input.mandate
    yield from _offer_reasons(line)
    yield from _allergen_reasons(line, mandate)
    yield from _blocked_reasons(line, mandate)
    yield from _allow_list_reasons(line, mandate)
    yield from _requirement_reasons(line, mandate)
    if line.substitutes_for is not None:
        yield from _substitution_reasons(line, line.substitutes_for, mandate)
    yield from _supply_reasons(line, policy_input)
    yield from _quantity_info_reasons(line)


def _offer_reasons(line: PolicyLine) -> Iterator[PolicyReason]:
    """
    What makes the offer unusable: the product can't be ordered, priced or quantified.
    """
    offer = line.offer
    ref = line.line_ref
    if offer.sales_blocked:
        yield _reason(PolicyReasonCode.SALES_BLOCKED, ref, "The product is sales-blocked.", {})
    if offer.earliest_date is None:
        yield _reason(
            PolicyReasonCode.NOT_DELIVERABLE, ref, "The product can't be delivered on any date.", {}
        )
    if offer.unit_price is None:
        yield _reason(
            PolicyReasonCode.NO_PRICE, ref, "Valio Aimo gave no price for the product.", {}
        )
    if offer.closing_time_passed:
        yield _reason(
            PolicyReasonCode.CLOSING_TIME_PASSED,
            ref,
            "The order cut-off for the delivery date has passed.",
            {"closingTime": offer.closing_time},
        )
    quantity = offer.quantity
    if quantity.sales_units is None:
        yield _reason(
            PolicyReasonCode.CONVERSION_UNAVAILABLE,
            ref,
            f"The quantity can't be converted from {quantity.requested_unit} to the product's sales unit.",
            {"requestedValue": quantity.requested_value, "requestedUnit": quantity.requested_unit},
        )


def _allergen_reasons(line: PolicyLine, mandate: MandateTerms) -> Iterator[PolicyReason]:
    strictness = mandate.allergen_strictness
    for allergen in mandate.excluded_allergens:
        status = AllergenStatus.of(line.product.allergens.get(allergen))
        facts = {"allergen": allergen, "declared": status.value}
        if status is AllergenStatus.CONTAINS:
            yield _reason(
                PolicyReasonCode.CONTAINS_EXCLUDED_ALLERGEN,
                line.line_ref,
                f"The product contains the excluded allergen {allergen}.",
                facts,
            )
        elif status is AllergenStatus.MAY_CONTAIN and strictness in (
            AllergenStrictness.MAY_CONTAIN,
            AllergenStrictness.DECLARED_FREE,
        ):
            yield _reason(
                PolicyReasonCode.MAY_CONTAIN_EXCLUDED_ALLERGEN,
                line.line_ref,
                f"The product may contain the excluded allergen {allergen}.",
                facts,
            )
        elif (
            strictness is AllergenStrictness.DECLARED_FREE
            and status is not AllergenStatus.FREE_FROM
        ):
            # Includes UNKNOWN: missing data is never free-from
            yield _reason(
                PolicyReasonCode.ALLERGEN_NOT_DECLARED_FREE,
                line.line_ref,
                f"The product isn't declared free from the excluded allergen {allergen}.",
                facts,
            )


def _blocked_reasons(line: PolicyLine, mandate: MandateTerms) -> Iterator[PolicyReason]:
    product = line.product
    if product.category_code in mandate.blocked_category_codes:
        yield _reason(
            PolicyReasonCode.BLOCKED_CATEGORY,
            line.line_ref,
            f"The product's category {product.category_code} is blocked.",
            {"categoryCode": product.category_code},
        )
    if product.vendor in mandate.blocked_vendors:
        yield _reason(
            PolicyReasonCode.BLOCKED_VENDOR,
            line.line_ref,
            f"The vendor {product.vendor} is blocked.",
            {"vendor": product.vendor},
        )


def _allow_list_reasons(line: PolicyLine, mandate: MandateTerms) -> Iterator[PolicyReason]:
    """
    An empty allow-list allows anything; an unknown value (None) is on no list.
    """
    product = line.product
    checks = (
        (PolicyReasonCode.CATEGORY_NOT_ALLOWED, "categoryCode", "The product's category",
         product.category_code, mandate.allowed_category_codes),
        (PolicyReasonCode.VENDOR_NOT_ALLOWED, "vendor", "The vendor",
         product.vendor, mandate.allowed_vendors),
        (PolicyReasonCode.ORIGIN_NOT_ALLOWED, "countryOfOrigin", "The product's origin",
         product.country_of_origin, mandate.allowed_countries_of_origin),
    )  # fmt: skip
    for code, fact, subject, value, allowed in checks:
        if allowed and value not in allowed:
            yield _reason(
                code,
                line.line_ref,
                f"{subject} {value} isn't on the allowed list."
                if value
                else f"{subject} is unknown, so it can't be on the allowed list.",
                {fact: value, "allowed": list(allowed)},
            )


def _requirement_reasons(line: PolicyLine, mandate: MandateTerms) -> Iterator[PolicyReason]:
    """
    Only what the product declares counts: an undeclared requirement is missing.
    """
    product = line.product
    checks = (
        (PolicyReasonCode.MISSING_REQUIRED_CLAIM, "claim",
         "The product doesn't declare the required claim {}.",
         {f"{c.type}_{c.element}": c in product.claims for c in mandate.required_claims}),
        (PolicyReasonCode.MISSING_REQUIRED_LABEL, "label",
         "The product doesn't carry the required label {}.",
         {label: label in product.labels for label in mandate.required_labels}),
        (PolicyReasonCode.MISSING_REQUIRED_DIET, "diet",
         "The product isn't declared suitable for the required diet {}.",
         {diet: diet in product.diets for diet in mandate.required_diets}),
    )  # fmt: skip
    for code, fact, message, declared in checks:
        for requirement, has_it in declared.items():
            if not has_it:
                yield _reason(code, line.line_ref, message.format(requirement), {fact: requirement})


def _substitution_reasons(
    line: PolicyLine, original: SubstitutedProduct, mandate: MandateTerms
) -> Iterator[PolicyReason]:
    ref = line.line_ref
    facts = {"originalProductCode": original.product_code}
    match mandate.substitution_policy:
        case SubstitutionPolicy.NEVER:
            yield _reason(
                PolicyReasonCode.SUBSTITUTION_NOT_ALLOWED,
                ref,
                f"The mandate allows no substitutes, and this line replaces {original.product_code}.",
                facts,
            )
        case SubstitutionPolicy.ALWAYS_NEEDS_APPROVAL:
            yield _reason(
                PolicyReasonCode.SUBSTITUTE_NEEDS_APPROVAL,
                ref,
                f"The mandate has every substitute approved, and this line replaces {original.product_code}.",
                facts,
            )
    yield from _substitute_price_reasons(line, original, mandate)


def _substitute_price_reasons(
    line: PolicyLine, original: SubstitutedProduct, mandate: MandateTerms
) -> Iterator[PolicyReason]:
    """
    Compares prices per buyer unit. When they can't be compared (a price is unknown or the
    two lines are in different buyer units), the increase can't be shown to be within
    bounds, so a human decides.
    """
    price = line.offer.price_per_buyer_unit
    original_price = original.offer.price_per_buyer_unit
    buyer_unit = line.offer.buyer_unit
    if (
        price is None
        or original_price is None
        or original_price <= 0
        or buyer_unit != original.offer.buyer_unit
    ):
        yield _reason(
            PolicyReasonCode.SUBSTITUTE_PRICE_INCREASE,
            line.line_ref,
            f"The substitute's price can't be compared with that of {original.product_code}.",
            {"originalProductCode": original.product_code, "comparable": False},
        )
        return

    increase_pct = (price - original_price) / original_price * 100
    maximum = mandate.max_substitute_price_increase_pct
    if increase_pct > maximum:
        shown_pct = increase_pct.quantize(_PCT_DISPLAY_STEP, rounding=ROUND_HALF_UP)
        yield _reason(
            PolicyReasonCode.SUBSTITUTE_PRICE_INCREASE,
            line.line_ref,
            f"The substitute costs {shown_pct}% more per {buyer_unit} than {original.product_code}, over the {maximum}% allowed.",
            {
                "originalProductCode": original.product_code,
                "comparable": True,
                "buyerUnit": buyer_unit,
                "originalPricePerBuyerUnit": original_price,
                "pricePerBuyerUnit": price,
                "increasePct": shown_pct,
                "maxIncreasePct": maximum,
            },
        )


def _supply_reasons(line: PolicyLine, policy_input: PolicyInput) -> Iterator[PolicyReason]:
    """
    Whether the product arrives as asked: enough stock, on time, reliably.
    """
    offer = line.offer
    ref = line.line_ref
    sales_units = offer.quantity.sales_units
    if (
        offer.available_amount is not None
        and sales_units is not None
        and offer.available_amount < sales_units
    ):
        yield _reason(
            PolicyReasonCode.PARTIAL_AVAILABILITY,
            ref,
            f"Only {offer.available_amount} of {sales_units} sales units are in stock.",
            {"availableAmount": offer.available_amount, "salesUnits": sales_units},
        )

    mandate = policy_input.mandate
    deliver_by = policy_input.deliver_by
    if offer.earliest_date is not None and offer.earliest_date > deliver_by:
        yield _reason(
            PolicyReasonCode.LATE_DELIVERY,
            ref,
            f"The earliest delivery is {offer.earliest_date.isoformat()}, after the requested {deliver_by.isoformat()}.",
            {"earliestDate": offer.earliest_date, "deliverBy": deliver_by},
            severity=Severity.NEEDS_HUMAN
            if mandate.later_delivery_needs_approval
            else Severity.INFO,
        )

    reliability = line.product.delivery_reliability
    minimum = mandate.min_delivery_reliability
    # No reliability data doesn't trigger the minimum
    if minimum is not None and reliability is not None and reliability < minimum:
        yield _reason(
            PolicyReasonCode.BELOW_MIN_RELIABILITY,
            ref,
            f"The product's delivery reliability {reliability:.1%} is below the minimum of {minimum:.1%}.",
            {"deliveryReliability": reliability, "minimum": minimum},
        )

    if offer.logistic_model is LogisticModel.TERMINAL:
        yield _reason(
            PolicyReasonCode.STOCK_UNKNOWN,
            ref,
            "The product ships from a terminal, so stock for the quantity can't be confirmed.",
            {"logisticModel": offer.logistic_model.value},
        )


def _quantity_info_reasons(line: PolicyLine) -> Iterator[PolicyReason]:
    quantity = line.offer.quantity
    conversion = quantity.conversion
    if conversion is not None and conversion.cross_check is not CrossCheck.AGREES:
        yield _reason(
            PolicyReasonCode.CONVERSION_UNCERTAIN,
            line.line_ref,
            f"The conversion of {conversion.per_sales_unit} {conversion.unit} per sales unit couldn't be confirmed against the catalog.",
            {
                "perSalesUnit": conversion.per_sales_unit,
                "buyerUnit": conversion.unit,
                "crossCheck": conversion.cross_check.value,
            },
        )
    if quantity.rounded_up:
        yield _reason(
            PolicyReasonCode.ROUNDED_TO_LOT_SIZE,
            line.line_ref,
            f"The quantity was rounded up to {quantity.sales_units} sales units to fit the lot size of {quantity.lot_size}.",
            {
                "requestedValue": quantity.requested_value,
                "requestedUnit": quantity.requested_unit,
                "salesUnits": quantity.sales_units,
                "lotSize": quantity.lot_size,
            },
        )


def _quote_reasons(policy_input: PolicyInput, quote_total: Decimal) -> Iterator[PolicyReason]:
    mandate = policy_input.mandate
    if quote_total > mandate.max_order_total:
        yield _reason(
            PolicyReasonCode.OVER_ORDER_LIMIT,
            None,
            f"The order total of €{quote_total} is over the €{mandate.max_order_total} limit per order.",
            {"orderTotal": quote_total, "limit": mandate.max_order_total},
        )
    elif quote_total > mandate.auto_approve_up_to:
        yield _reason(
            PolicyReasonCode.OVER_AUTO_APPROVE_LIMIT,
            None,
            f"The order total of €{quote_total} is over the €{mandate.auto_approve_up_to} that can be approved automatically.",
            {"orderTotal": quote_total, "limit": mandate.auto_approve_up_to},
        )

    # Caps count what the period already committed, so splitting an order doesn't
    # get round them
    period_spend = policy_input.period_spend
    if period_spend + quote_total > mandate.period_spend_cap:
        yield _reason(
            PolicyReasonCode.OVER_PERIOD_CAP,
            None,
            f"This order of €{quote_total} on top of €{period_spend} already spent this period is over the €{mandate.period_spend_cap} period cap.",
            {
                "periodSpend": period_spend,
                "orderTotal": quote_total,
                "cap": mandate.period_spend_cap,
            },
        )
    for category_cap in mandate.category_spend_caps:
        category = category_cap.category_code
        spent = policy_input.category_period_spend.get(category, Decimal(0))
        total = _total(
            line for line in policy_input.lines if line.product.category_code == category
        )
        # Only a quote that adds to the category can take it over its cap
        if total > 0 and spent + total > category_cap.cap:
            yield _reason(
                PolicyReasonCode.OVER_CATEGORY_CAP,
                None,
                f"This order's €{total} in category {category} on top of €{spent} already spent this period is over the category's €{category_cap.cap} cap.",
                {
                    "categoryCode": category,
                    "periodSpend": spent,
                    "orderTotal": total,
                    "cap": category_cap.cap,
                },
            )


def _total(lines: Iterable[PolicyLine]) -> Decimal:
    """
    Net EUR of the lines that have a total; a line without one is rejected anyway.
    """
    return sum(
        (line.offer.line_total for line in lines if line.offer.line_total is not None),
        Decimal(0),
    )


def _reason(
    code: PolicyReasonCode,
    line_ref: str | None,
    message: str,
    facts: Mapping[str, Any],
    severity: Severity | None = None,
) -> PolicyReason:
    return PolicyReason(
        code=code,
        severity=severity or REASON_SEVERITY[code],
        line_ref=line_ref,
        message=message,
        facts=facts,
    )


def _most_severe(reasons: list[PolicyReason]) -> PolicyOutcome:
    return max(
        (reason.severity for reason in reasons), key=lambda s: s.rank, default=Severity.INFO
    ).outcome
