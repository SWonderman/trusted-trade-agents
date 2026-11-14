from enum import StrEnum


class Language(StrEnum):
    """
    ISO 639-1 language the catalogue has texts in.
    """

    FI = "fi"
    SV = "sv"
    EN = "en"


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


class AllergenStatus(StrEnum):
    """
    What is known about one allergen of a product: its AllergenContainment, or
    UNKNOWN when the product has no row for it.
    """

    CONTAINS = AllergenContainment.CONTAINS.value
    MAY_CONTAIN = AllergenContainment.MAY_CONTAIN.value
    UNDECLARED = AllergenContainment.UNDECLARED.value
    FREE_FROM = AllergenContainment.FREE_FROM.value
    UNKNOWN = "UNKNOWN"

    @classmethod
    def of(cls, containment: AllergenContainment | None) -> "AllergenStatus":
        return cls.UNKNOWN if containment is None else cls[containment.name]


class AllergenStrictness(StrEnum):
    """
    How strictly an allergen should be excluded.
    """

    CONTAINS = "contains"  # drop products declared CONTAINS
    MAY_CONTAIN = "may_contain"  # also drop MAY_CONTAIN
    DECLARED_FREE = "declared_free"  # keep only products declared FREE_FROM every one


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
