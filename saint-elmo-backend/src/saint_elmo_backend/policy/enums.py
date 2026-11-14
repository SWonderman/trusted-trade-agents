from enum import StrEnum


class PolicyOutcome(StrEnum):
    AUTO_APPROVE = "AUTO_APPROVE"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    REJECT = "REJECT"


class Severity(StrEnum):
    """
    How much one reason weighs. INFO is only stated.
    """

    INFO = "INFO"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    REJECT = "REJECT"

    @property
    def rank(self) -> int:
        return list(Severity).index(self)

    @property
    def outcome(self) -> PolicyOutcome:
        return {
            Severity.INFO: PolicyOutcome.AUTO_APPROVE,
            Severity.NEEDS_HUMAN: PolicyOutcome.NEEDS_HUMAN,
            Severity.REJECT: PolicyOutcome.REJECT,
        }[self]


class PolicyReasonCode(StrEnum):
    """
    The policy's reason code catalogue. Each code has a fixed severity
    (`REASON_SEVERITY`), except LATE_DELIVERY, which the mandate decides.
    """

    # Reject
    SALES_BLOCKED = "SALES_BLOCKED"
    NOT_DELIVERABLE = "NOT_DELIVERABLE"
    NO_PRICE = "NO_PRICE"
    CLOSING_TIME_PASSED = "CLOSING_TIME_PASSED"
    CONTAINS_EXCLUDED_ALLERGEN = "CONTAINS_EXCLUDED_ALLERGEN"
    MAY_CONTAIN_EXCLUDED_ALLERGEN = "MAY_CONTAIN_EXCLUDED_ALLERGEN"
    ALLERGEN_NOT_DECLARED_FREE = "ALLERGEN_NOT_DECLARED_FREE"
    BLOCKED_CATEGORY = "BLOCKED_CATEGORY"
    BLOCKED_VENDOR = "BLOCKED_VENDOR"
    SUBSTITUTION_NOT_ALLOWED = "SUBSTITUTION_NOT_ALLOWED"
    OVER_ORDER_LIMIT = "OVER_ORDER_LIMIT"
    CONVERSION_UNAVAILABLE = "CONVERSION_UNAVAILABLE"
    # Needs a human
    CATEGORY_NOT_ALLOWED = "CATEGORY_NOT_ALLOWED"
    VENDOR_NOT_ALLOWED = "VENDOR_NOT_ALLOWED"
    ORIGIN_NOT_ALLOWED = "ORIGIN_NOT_ALLOWED"
    MISSING_REQUIRED_CLAIM = "MISSING_REQUIRED_CLAIM"
    MISSING_REQUIRED_LABEL = "MISSING_REQUIRED_LABEL"
    MISSING_REQUIRED_DIET = "MISSING_REQUIRED_DIET"
    OVER_AUTO_APPROVE_LIMIT = "OVER_AUTO_APPROVE_LIMIT"
    OVER_PERIOD_CAP = "OVER_PERIOD_CAP"
    OVER_CATEGORY_CAP = "OVER_CATEGORY_CAP"
    PARTIAL_AVAILABILITY = "PARTIAL_AVAILABILITY"
    LATE_DELIVERY = "LATE_DELIVERY"
    BELOW_MIN_RELIABILITY = "BELOW_MIN_RELIABILITY"
    SUBSTITUTE_NEEDS_APPROVAL = "SUBSTITUTE_NEEDS_APPROVAL"
    SUBSTITUTE_PRICE_INCREASE = "SUBSTITUTE_PRICE_INCREASE"
    # Info
    STOCK_UNKNOWN = "STOCK_UNKNOWN"
    CONVERSION_UNCERTAIN = "CONVERSION_UNCERTAIN"
    ROUNDED_TO_LOT_SIZE = "ROUNDED_TO_LOT_SIZE"


REASON_SEVERITY: dict[PolicyReasonCode, Severity] = {
    **dict.fromkeys(
        (
            PolicyReasonCode.SALES_BLOCKED,
            PolicyReasonCode.NOT_DELIVERABLE,
            PolicyReasonCode.NO_PRICE,
            PolicyReasonCode.CLOSING_TIME_PASSED,
            PolicyReasonCode.CONTAINS_EXCLUDED_ALLERGEN,
            PolicyReasonCode.MAY_CONTAIN_EXCLUDED_ALLERGEN,
            PolicyReasonCode.ALLERGEN_NOT_DECLARED_FREE,
            PolicyReasonCode.BLOCKED_CATEGORY,
            PolicyReasonCode.BLOCKED_VENDOR,
            PolicyReasonCode.SUBSTITUTION_NOT_ALLOWED,
            PolicyReasonCode.OVER_ORDER_LIMIT,
            PolicyReasonCode.CONVERSION_UNAVAILABLE,
        ),
        Severity.REJECT,
    ),
    **dict.fromkeys(
        (
            PolicyReasonCode.CATEGORY_NOT_ALLOWED,
            PolicyReasonCode.VENDOR_NOT_ALLOWED,
            PolicyReasonCode.ORIGIN_NOT_ALLOWED,
            PolicyReasonCode.MISSING_REQUIRED_CLAIM,
            PolicyReasonCode.MISSING_REQUIRED_LABEL,
            PolicyReasonCode.MISSING_REQUIRED_DIET,
            PolicyReasonCode.OVER_AUTO_APPROVE_LIMIT,
            PolicyReasonCode.OVER_PERIOD_CAP,
            PolicyReasonCode.OVER_CATEGORY_CAP,
            PolicyReasonCode.PARTIAL_AVAILABILITY,
            PolicyReasonCode.BELOW_MIN_RELIABILITY,
            PolicyReasonCode.SUBSTITUTE_NEEDS_APPROVAL,
            PolicyReasonCode.SUBSTITUTE_PRICE_INCREASE,
        ),
        Severity.NEEDS_HUMAN,
    ),
    **dict.fromkeys(
        (
            PolicyReasonCode.STOCK_UNKNOWN,
            PolicyReasonCode.CONVERSION_UNCERTAIN,
            PolicyReasonCode.ROUNDED_TO_LOT_SIZE,
        ),
        Severity.INFO,
    ),
}
