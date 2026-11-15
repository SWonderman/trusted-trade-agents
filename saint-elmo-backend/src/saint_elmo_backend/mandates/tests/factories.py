"""
Mandate terms for integration tests.
"""

from decimal import Decimal

from saint_elmo_backend.mandates.dtos import MandateTerms
from saint_elmo_backend.mandates.enums import SpendPeriod, SubstitutionPolicy


def make_terms() -> MandateTerms:
    """
    Spend limits and nothing else: every product and vendor allowed. Change fields with
    `dataclasses.replace`.
    """

    return MandateTerms(
        max_order_total=Decimal("1000"),
        period_spend_cap=Decimal("5000"),
        spend_period=SpendPeriod.MONTH,
        auto_approve_up_to=Decimal("500"),
        substitution_policy=SubstitutionPolicy.IF_REQUIREMENTS_HOLD,
        max_substitute_price_increase_pct=Decimal("10"),
    )
