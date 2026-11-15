from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from saint_elmo_backend.mandates.enums import SpendPeriod
from saint_elmo_backend.mandates.services import spend_period_bounds

HELSINKI = ZoneInfo("Europe/Helsinki")


def _helsinki(*args: int) -> datetime:
    return datetime(*args, tzinfo=HELSINKI)


@pytest.mark.parametrize(
    ("period", "now", "start", "end"),
    [
        # Saturday 14 Nov 2026 -> Monday 9 Nov to Monday 16 Nov
        (
            SpendPeriod.WEEK,
            _helsinki(2026, 11, 14, 12, 0),
            _helsinki(2026, 11, 9),
            _helsinki(2026, 11, 16),
        ),
        # Late Sunday night in Helsinki is still the week that began on Monday
        (
            SpendPeriod.WEEK,
            _helsinki(2026, 11, 15, 23, 59),
            _helsinki(2026, 11, 9),
            _helsinki(2026, 11, 16),
        ),
        # 22:30 UTC on Sunday is already Monday 00:30 in Helsinki: a new week
        (
            SpendPeriod.WEEK,
            datetime(2026, 11, 15, 22, 30, tzinfo=UTC),
            _helsinki(2026, 11, 16),
            _helsinki(2026, 11, 23),
        ),
        # The week of the switch to summer time (29 Mar 2026) is 167 hours long
        (
            SpendPeriod.WEEK,
            _helsinki(2026, 3, 29, 12, 0),
            _helsinki(2026, 3, 23),
            _helsinki(2026, 3, 30),
        ),
        (
            SpendPeriod.MONTH,
            _helsinki(2026, 11, 14, 12, 0),
            _helsinki(2026, 11, 1),
            _helsinki(2026, 12, 1),
        ),
        # December rolls over into the next year
        (
            SpendPeriod.MONTH,
            _helsinki(2026, 12, 31, 23, 59),
            _helsinki(2026, 12, 1),
            _helsinki(2027, 1, 1),
        ),
        # 22:30 UTC on 31 Jan is 1 Feb in Helsinki
        (
            SpendPeriod.MONTH,
            datetime(2027, 1, 31, 22, 30, tzinfo=UTC),
            _helsinki(2027, 2, 1),
            _helsinki(2027, 3, 1),
        ),
    ],
    ids=[
        "week",
        "sunday night",
        "monday in helsinki, sunday in utc",
        "week with dst switch",
        "month",
        "december",
        "next month in helsinki, not yet in utc",
    ],
)
def test_spend_period_bounds(period, now, start, end):
    assert spend_period_bounds(period, now) == (start, end)
