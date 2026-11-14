"""
Substitute ranking: candidates scored on their documented weights. Pure, so no database
or API.
"""

from dataclasses import replace
from decimal import Decimal

from saint_elmo_backend.substitutes.enums import Tier
from saint_elmo_backend.substitutes.ranking import CandidateFacts, rank_candidates

# On time, covering the quantity, at 1.50 €/L, 95% reliable, no labels gained, 1.2 kg CO2
ON_TIME = CandidateFacts(
    product_code="100001",
    curated=False,
    meets_deadline=True,
    covers_quantity=True,
    price_per_buyer_unit=Decimal("1.50"),
    delivery_reliability=Decimal("0.95"),
    labels_gained=0,
    carbon_footprint=Decimal("1.2"),
)


def _codes(ranked) -> list[str]:
    return [candidate.facts.product_code for candidate in ranked]


def test_a_late_candidate_ranks_below_an_on_time_one_even_when_cheaper():
    late = replace(
        ON_TIME, product_code="100002", meets_deadline=False, price_per_buyer_unit=Decimal("1")
    )

    ranked = rank_candidates([late, ON_TIME])

    assert _codes(ranked) == ["100001", "100002"]
    assert [candidate.rank for candidate in ranked] == [1, 2]
    # Delivery 40 + price 30 * 1 / 1.5 = 20 + reliability 15 * 0.95 = 14.25 + CO2 5
    assert ranked[0].score == Decimal("79.25")


def test_unknown_reliability_counts_as_the_mean_of_the_known_not_as_bad():
    reliable = replace(ON_TIME, product_code="100002", delivery_reliability=Decimal("0.99"))
    unknown = replace(ON_TIME, product_code="100003", delivery_reliability=None)

    ranked = rank_candidates([unknown, reliable, ON_TIME])

    assert _codes(ranked) == ["100002", "100003", "100001"]
    # The mean of 0.95 and 0.99 is 0.97: 40 + 30 + 15 * 0.97 + 5
    assert ranked[1].score == Decimal("89.55")


def test_equal_scores_rank_a_curated_substitute_first_then_by_code():
    curated = replace(ON_TIME, product_code="100009", curated=True)
    other = replace(ON_TIME, product_code="100005")

    ranked = rank_candidates([ON_TIME, other, curated])

    assert _codes(ranked) == ["100009", "100001", "100005"]
    assert len({candidate.score for candidate in ranked}) == 1


def test_tiers_are_best_better_then_good_in_rank_order():
    candidates = [
        replace(ON_TIME, product_code=f"10000{i}", price_per_buyer_unit=Decimal(f"1.{i}"))
        for i in range(1, 6)
    ]

    ranked = rank_candidates(candidates)

    assert [(c.facts.product_code, c.tier) for c in ranked] == [
        ("100001", Tier.BEST),
        ("100002", Tier.BETTER),
        ("100003", Tier.GOOD),
        ("100004", Tier.GOOD),
        ("100005", Tier.GOOD),
    ]


def test_labels_gained_and_lower_co2_lift_an_otherwise_equal_candidate():
    organic = replace(ON_TIME, product_code="100002", labels_gained=3)
    greener = replace(ON_TIME, product_code="100003", carbon_footprint=Decimal("0.6"))

    ranked = rank_candidates([ON_TIME, greener, organic])

    assert _codes(ranked) == ["100002", "100003", "100001"]
    # Labels count at most 2: 40 + 30 + 14.25 + 10 + CO2 5 * 0.6 / 1.2
    assert ranked[0].score == Decimal("96.75")
    # 40 + 30 + 14.25 + 5
    assert ranked[1].score == Decimal("89.25")


def test_an_unknown_price_scores_no_price_points():
    unpriced = replace(ON_TIME, product_code="100002", price_per_buyer_unit=None)

    ranked = rank_candidates([unpriced, ON_TIME])

    assert _codes(ranked) == ["100001", "100002"]
    assert ranked[1].score == Decimal("59.25")


def test_delivery_outranks_any_price_difference():
    # Scores 69.25 against the on-time candidate's 67.58, but arrives late
    late_and_cheap = replace(
        ON_TIME, product_code="100001", meets_deadline=False, price_per_buyer_unit=Decimal("0.5")
    )
    on_time = replace(ON_TIME, product_code="100002", price_per_buyer_unit=Decimal("1.8"))

    ranked = rank_candidates([late_and_cheap, on_time])

    assert _codes(ranked) == ["100002", "100001"]
    assert [c.score for c in ranked] == [Decimal("67.58"), Decimal("69.25")]


def test_meeting_one_delivery_condition_outranks_meeting_neither():
    # Late and short, but the cheapest: 0 + 0 + 30 + 14.25 + 5 = 49.25
    late_partial = replace(
        ON_TIME,
        product_code="100001",
        meets_deadline=False,
        covers_quantity=False,
        price_per_buyer_unit=Decimal("0.5"),
    )
    # On time but short at 3x the price: 20 + 5 + 14.25 + 5 = 44.25
    on_time_partial = replace(
        ON_TIME, product_code="100003", covers_quantity=False, price_per_buyer_unit=Decimal("3")
    )
    # Late but covering, at 1.5: 20 + 10 + 14.25 + 5 = 49.25
    late_full = replace(ON_TIME, product_code="100002", meets_deadline=False)

    ranked = rank_candidates([late_partial, on_time_partial, late_full])

    # One condition each for the first two, so their score decides; then neither
    assert _codes(ranked) == ["100002", "100003", "100001"]
