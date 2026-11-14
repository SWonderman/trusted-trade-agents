"""
GS1 GDSN code lists used by the product data (allergens, nutrients, units, claims, ...).

The XML files next to this module are GS1 Sweden's machine-readable republication of
the official GDSN code lists (https://gs1.se/services/codelist/3.1/<term>.xml). Each
file records the list's URN and GDD version; to update a list, replace its file.
"""

import xml.etree.ElementTree as ET

from dataclasses import dataclass
from pathlib import Path

_DIR = Path(__file__).parent

ALLERGEN_TYPE = "AllergenTypeCode"
NUTRIENT_TYPE = "NutrientTypeCode"
MEASUREMENT_UNIT = "MeasurementUnitCode_GDSN"
CLAIM_TYPE = "ClaimTypeCode"
CLAIM_ELEMENT = "ClaimElementCode"
DIET_TYPE = "DietTypeCode"
PACKAGING_LABEL = "PackagingMarkedLabelAccreditationCode"
PRODUCT_ACTIVITY_TYPE = "ProductActivityTypeCode"
CATCH_METHOD = "CatchMethodCode"
CATCH_AREA = "CatchAreaCode_GDSN"


@dataclass(frozen=True)
class CodeListEntry:
    code: str
    name: str | None
    definition: str | None
    is_standard: bool


# Codes the GS1 list contains but leaves without an English name
_NAME_OVERRIDES: dict[str, dict[str, str]] = {
    PACKAGING_LABEL: {
        # GS1 Web Vocabulary v1.18, https://ref.gs1.org/voc/data/gs1Voc.jsonld
        "FINNISH_HEART_SYMBOL": "Finnish Heart Symbol",
        "MADE_IN_FINLAND_FLAG_WITH_KEY": "Made in Finland",
        "OFFICIAL_ECO_LABEL_SUN": "Luomo Sun Sign",
        # No GS1 global source names these; the label's own name
        "DOLPHIN_SAFE": "Dolphin Safe",
        "PUHTAASTI_KOTIMAINEN": "Puhtaasti kotimainen",
    },
}

# Codes the data uses that are in no GS1 list. Only codes whose meaning follows from
# GS1 parts are named; the rest stay unnamed rather than guessed.
_NON_STANDARD: dict[str, dict[str, str]] = {
    NUTRIENT_TYPE: {
        # Synkka joins nutrient ENER- ("Energy") with the unit code (KJO, E14)
        "ENER-KJO": "Energy (kilojoules)",
        "ENER-E14": "Energy (kilocalories)",
    },
}


def _english(element: ET.Element, tag: str) -> str | None:
    for child in element.findall(tag):
        if child.get("languageCode") == "en" and child.text and child.text.strip():
            return child.text.strip()
    return None


def load_code_list(list_name: str) -> dict[str, CodeListEntry]:
    """
    Read one vendored code list into {code: entry}, plus its named non-standard codes.

    A few codes appear twice in the source files; the first entry, which carries the
    fuller name, wins.
    """
    root = ET.parse(_DIR / f"{list_name}.xml").getroot()
    overrides = _NAME_OVERRIDES.get(list_name, {})

    entries: dict[str, CodeListEntry] = {}
    for element in root.findall("code"):
        code = (element.findtext("value") or "").strip()
        if not code or code in entries:
            continue

        entries[code] = CodeListEntry(
            code=code,
            name=_english(element, "name") or overrides.get(code),
            definition=_english(element, "description"),
            is_standard=True,
        )

    for code, name in _NON_STANDARD.get(list_name, {}).items():
        entries.setdefault(
            code, CodeListEntry(code=code, name=name, definition=None, is_standard=False)
        )

    return entries
