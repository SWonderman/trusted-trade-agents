from enum import StrEnum


class VatCode(StrEnum):
    """
    Finnish VAT class. Indicative only: the price API's `tax.taxRate` is authoritative.
    """

    STANDARD = "STANDARD"  # 25.5 %
    MEDIUM = "MEDIUM"  # 13.5 %, reduced rate for food
    LOW = "LOW"  # 10 %
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AllergenContainment(StrEnum):
    """
    How an allergen relates to a product. A product with no row for an allergen has
    UNKNOWN status for it - absence of data is never the same as FREE_FROM.
    """

    CONTAINS = "CONTAINS"
    MAY_CONTAIN = "MAY_CONTAIN"
    UNDECLARED = "UNDECLARED"
    FREE_FROM = "FREE_FROM"


class PackagingLevel(StrEnum):
    BASE_UNIT_OR_EACH = "BASE_UNIT_OR_EACH"
    CASE = "CASE"
    PALLET = "PALLET"


class FishProductionMethod(StrEnum):
    AQUACULTURE = "AQUACULTURE"
    MARINE_FISHERY = "MARINE_FISHERY"
    INLAND_FISHERY = "INLAND_FISHERY"


class SafetyStatementType(StrEnum):
    HAZARD = "HAZARD"
    PRECAUTIONARY = "PRECAUTIONARY"
