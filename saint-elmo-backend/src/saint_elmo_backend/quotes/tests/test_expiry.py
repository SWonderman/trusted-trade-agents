"""
When a quote expires: the earliest of its lines' offer deadlines and its time-to-live.
"""

from datetime import UTC, datetime, timedelta

from saint_elmo_backend.quotes.services import quote_expiry

CREATED_AT = datetime(2026, 11, 14, 10, 0, tzinfo=UTC)
TTL = timedelta(minutes=15)


def test_without_sooner_deadlines_a_quote_lasts_its_time_to_live():
    far = datetime(9999, 12, 31, tzinfo=UTC)

    assert quote_expiry(CREATED_AT, TTL, [far, None]) == datetime(2026, 11, 14, 10, 15, tzinfo=UTC)


def test_the_soonest_line_deadline_cuts_the_quote_short():
    # e.g. one line's closing time for deliverBy, another's price validTo
    closing_time = datetime(2026, 11, 14, 10, 5, tzinfo=UTC)
    price_valid_to = datetime(2026, 11, 14, 10, 10, tzinfo=UTC)

    assert quote_expiry(CREATED_AT, TTL, [price_valid_to, None, closing_time]) == closing_time


def test_a_line_without_a_known_deadline_doesnt_limit_it():
    assert quote_expiry(CREATED_AT, TTL, [None]) == CREATED_AT + TTL


def test_a_deadline_already_passed_doesnt_expire_a_new_quote():
    # The policy rejects such a line (CLOSING_TIME_PASSED); the quote still starts valid
    passed = CREATED_AT - timedelta(days=1)

    assert quote_expiry(CREATED_AT, TTL, [passed]) == CREATED_AT + TTL
