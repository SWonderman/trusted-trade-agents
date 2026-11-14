"""
Substitute ranking: every candidate gets a score out of 100 from these inputs, weighted
in this order of importance.

| Input                 | Points | How                                                    |
| --------------------- | ------ | ------------------------------------------------------ |
| Delivery              | 40     | 20 for meeting deliverBy, 20 for covering the quantity |
| Price per buyer unit  | 30     | 30 x cheapest candidate's price / this price; 0 if unknown |
| Delivery reliability  | 15     | 15 x reliability; unknown counts as the mean of the known |
| Labels gained         | 10     | 5 per label the original lacks, at most 2              |
| CO2 estimate          | 5      | 5 x lowest candidate's estimate / this one; unknown counts as the mean |

An unknown reliability or CO2 estimate is neutral, not bad.

Delivery comes first outright, not just by weight: candidates are ordered by how many of
the two delivery conditions they meet, and only then by score, so no price, reliability,
label or CO2 advantage lifts a late or short candidate above one that delivers. Equal
scores rank curated substitutes first, then by product code, so the ranking is
deterministic.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from saint_elmo_backend.substitutes.enums import Tier

DEADLINE_POINTS = Decimal("20")
QUANTITY_POINTS = Decimal("20")
PRICE_POINTS = Decimal("30")
RELIABILITY_POINTS = Decimal("15")
POINTS_PER_LABEL = Decimal("5")
MAX_LABELS_SCORED = 2
CARBON_POINTS = Decimal("5")

_SCORE_STEP = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class CandidateFacts:
    """
    What a candidate is ranked on, judged against the original and the requested need.
    """

    product_code: str
    curated: bool
    meets_deadline: bool
    # An unknown available amount (TERMINAL) counts as covering
    covers_quantity: bool
    # Net EUR; None when the price or the conversion is unknown
    price_per_buyer_unit: Decimal | None
    delivery_reliability: Decimal | None
    # Labels the candidate carries and the original doesn't
    labels_gained: int
    # kg CO2-eq per kg, a product-group estimate
    carbon_footprint: Decimal | None


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    facts: CandidateFacts
    # Out of 100, to the cent
    score: Decimal
    # From 1
    rank: int
    tier: Tier


def rank_candidates(candidates: Sequence[CandidateFacts]) -> list[RankedCandidate]:
    cheapest = _lowest(c.price_per_buyer_unit for c in candidates)
    lowest_carbon = _lowest(c.carbon_footprint for c in candidates)
    neutral_reliability = _mean(c.delivery_reliability for c in candidates)
    neutral_carbon = _mean(c.carbon_footprint for c in candidates)

    def score(candidate: CandidateFacts) -> Decimal:
        points = Decimal(0)
        if candidate.meets_deadline:
            points += DEADLINE_POINTS
        if candidate.covers_quantity:
            points += QUANTITY_POINTS
        points += _relative(PRICE_POINTS, cheapest, candidate.price_per_buyer_unit)
        reliability = candidate.delivery_reliability
        points += RELIABILITY_POINTS * (
            reliability if reliability is not None else neutral_reliability
        )
        points += POINTS_PER_LABEL * min(candidate.labels_gained, MAX_LABELS_SCORED)
        carbon = candidate.carbon_footprint
        points += _relative(
            CARBON_POINTS, lowest_carbon, carbon if carbon is not None else neutral_carbon
        )
        return points.quantize(_SCORE_STEP, rounding=ROUND_HALF_UP)

    scored = sorted(
        ((score(c), c) for c in candidates),
        key=lambda pair: (
            -_delivery_band(pair[1]),
            -pair[0],
            not pair[1].curated,
            pair[1].product_code,
        ),
    )
    return [
        RankedCandidate(facts=candidate, score=points, rank=rank, tier=_tier(rank))
        for rank, (points, candidate) in enumerate(scored, 1)
    ]


def _delivery_band(candidate: CandidateFacts) -> int:
    """
    How many of meeting deliverBy and covering the quantity the candidate manages: 0-2.
    """
    return int(candidate.meets_deadline) + int(candidate.covers_quantity)


def _tier(rank: int) -> Tier:
    return {1: Tier.BEST, 2: Tier.BETTER}.get(rank, Tier.GOOD)


def _relative(points: Decimal, best: Decimal | None, value: Decimal | None) -> Decimal:
    """
    Full points for the best (lowest) value, proportionally fewer for higher ones; none
    for an unknown value.
    """
    if best is None or value is None or value <= 0:
        return Decimal(0)
    return points * best / value


def _lowest(values) -> Decimal | None:
    return min((v for v in values if v is not None and v > 0), default=None)


def _mean(values) -> Decimal:
    known = [v for v in values if v is not None]
    return sum(known, Decimal(0)) / len(known) if known else Decimal(0)
