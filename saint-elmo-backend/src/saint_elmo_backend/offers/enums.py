from enum import StrEnum


class OfferReasonCode(StrEnum):
    """
    The shortfall and data codes an offer can carry, a subset of the policy's reason
    code catalogue (#13). An offer only states them; it judges nothing.
    """

    PARTIAL_AVAILABILITY = "PARTIAL_AVAILABILITY"
    LATE_DELIVERY = "LATE_DELIVERY"
    NOT_DELIVERABLE = "NOT_DELIVERABLE"
    SALES_BLOCKED = "SALES_BLOCKED"
    NO_PRICE = "NO_PRICE"
    CLOSING_TIME_PASSED = "CLOSING_TIME_PASSED"
    CONVERSION_UNAVAILABLE = "CONVERSION_UNAVAILABLE"
    CONVERSION_UNCERTAIN = "CONVERSION_UNCERTAIN"


class ConversionBasis(StrEnum):
    # Buyer units (L, KG) per sales unit = catalog price / comparison price
    PRICE_COMPARISON = "PRICE_COMPARISON"
    # Another of the product's units (e.g. ST for a product sold per KI), by unit sizes
    PACKAGING_UNITS = "PACKAGING_UNITS"


class CrossCheck(StrEnum):
    AGREES = "AGREES"
    DISAGREES = "DISAGREES"
    UNCHECKED = "UNCHECKED"


class LogisticModel(StrEnum):
    STOCK = "STOCK"
    TERMINAL = "TERMINAL"
