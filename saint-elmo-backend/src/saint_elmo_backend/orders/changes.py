"""
What moved between the offers a quote was judged on and the live offers an order
re-check got. The order follows the new policy result either way; the changes tell the
agent and the approver why it may differ from the quote.
"""

from collections.abc import Mapping
from typing import Any

# Change field -> its path in an offer's JSON, as `POST /offers` returns it
_COMPARED_FIELDS: dict[str, tuple[str, ...]] = {
    "unitPrice": ("price", "perSalesUnit", "net"),
    "availableAmount": ("availability", "availableAmount"),
    "earliestDate": ("availability", "earliestDate"),
    "closingTime": ("availability", "closingTime"),
    "salesBlocked": ("availability", "salesBlocked"),
}


def order_changes(
    quoted: Mapping[str, dict[str, Any]], live: Mapping[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    `[{lineRef, field, quoted, now}]` for every compared field that differs, lines in
    the order of `quoted`. Both map a line ref to that line's offer JSON; a price or
    availability the live offer no longer has compares as null.
    """
    return [
        {"lineRef": line_ref, "field": field, "quoted": before, "now": after}
        for line_ref, quoted_offer in quoted.items()
        for field, path in _COMPARED_FIELDS.items()
        if (before := _at(quoted_offer, path)) != (after := _at(live[line_ref], path))
    ]


def _at(offer: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = offer
    for key in path:
        if value is None:
            return None
        value = value.get(key)
    return value
