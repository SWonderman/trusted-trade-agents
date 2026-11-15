from enum import StrEnum


class SpendPeriod(StrEnum):
    """
    The calendar period a mandate's period spend cap covers.
    """

    WEEK = "WEEK"  # Monday to Sunday
    MONTH = "MONTH"


class SubstitutionPolicy(StrEnum):
    """
    When a substitute the agent proposes may go through without a human.
    """

    NEVER = "NEVER"
    IF_REQUIREMENTS_HOLD = "IF_REQUIREMENTS_HOLD"
    ALWAYS_NEEDS_APPROVAL = "ALWAYS_NEEDS_APPROVAL"
