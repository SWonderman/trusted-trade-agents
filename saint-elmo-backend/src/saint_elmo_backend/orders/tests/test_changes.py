"""
What changed between the offer a quote line was quoted with and the live offer an order
re-check got.
"""

from saint_elmo_backend.orders.changes import order_changes


def _offer(**availability) -> dict:
    """
    An offer in the JSON shape `POST /offers` returns, with only the fields compared.
    """
    return {
        "price": {"perSalesUnit": {"net": 31.31, "gross": 35.69}},
        "availability": {
            "availableAmount": 120.0,
            "earliestDate": "2030-06-03",
            "closingTime": "2030-06-01T13:00:00Z",
            "salesBlocked": False,
            **availability,
        },
    }


def test_an_unchanged_offer_has_no_changes():
    assert order_changes({"1": _offer()}, {"1": _offer()}) == []


def test_a_new_price_is_reported_per_sales_unit_net():
    repriced = _offer()
    repriced["price"]["perSalesUnit"]["net"] = 34.10

    assert order_changes({"1": _offer()}, {"1": repriced}) == [
        {"lineRef": "1", "field": "unitPrice", "quoted": 31.31, "now": 34.10}
    ]


def test_availability_changes_are_reported_field_by_field_in_line_order():
    quoted = {"1": _offer(), "2": _offer()}
    live = {
        "1": _offer(availableAmount=40.0),
        "2": _offer(earliestDate="2030-06-05", salesBlocked=True),
    }

    assert order_changes(quoted, live) == [
        {"lineRef": "1", "field": "availableAmount", "quoted": 120.0, "now": 40.0},
        {"lineRef": "2", "field": "earliestDate", "quoted": "2030-06-03", "now": "2030-06-05"},
        {"lineRef": "2", "field": "salesBlocked", "quoted": False, "now": True},
    ]


def test_a_price_or_availability_that_disappeared_shows_as_null():
    gone = {"price": None, "availability": None}

    changes = order_changes({"1": _offer()}, {"1": gone})

    assert {"lineRef": "1", "field": "unitPrice", "quoted": 31.31, "now": None} in changes
    assert {"lineRef": "1", "field": "salesBlocked", "quoted": False, "now": None} in changes
    assert len(changes) == 5
