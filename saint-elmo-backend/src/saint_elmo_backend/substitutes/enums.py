from enum import StrEnum


class Tier(StrEnum):
    """
    A ranked substitute's label, in rank order: the first is BEST, the second BETTER,
    every other GOOD.
    """

    BEST = "BEST"
    BETTER = "BETTER"
    GOOD = "GOOD"


class SubstitutesReasonCode(StrEnum):
    NO_SUBSTITUTES_FOUND = "NO_SUBSTITUTES_FOUND"
