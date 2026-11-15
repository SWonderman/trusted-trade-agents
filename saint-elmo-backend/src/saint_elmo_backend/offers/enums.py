from enum import StrEnum

from saint_elmo_backend.policy.enums import PolicyReasonCode


class OfferReasonCode(StrEnum):
    """
    The shortfall and data codes an offer can carry, a subset of the policy's reason
    code catalogue. An offer only states them; it judges nothing.
    """

    PARTIAL_AVAILABILITY = PolicyReasonCode.PARTIAL_AVAILABILITY.value
    LATE_DELIVERY = PolicyReasonCode.LATE_DELIVERY.value
    NOT_DELIVERABLE = PolicyReasonCode.NOT_DELIVERABLE.value
    SALES_BLOCKED = PolicyReasonCode.SALES_BLOCKED.value
    NO_PRICE = PolicyReasonCode.NO_PRICE.value
    CLOSING_TIME_PASSED = PolicyReasonCode.CLOSING_TIME_PASSED.value
    CONVERSION_UNAVAILABLE = PolicyReasonCode.CONVERSION_UNAVAILABLE.value
    CONVERSION_UNCERTAIN = PolicyReasonCode.CONVERSION_UNCERTAIN.value


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
