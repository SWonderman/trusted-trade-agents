"""
Smoke test against the real Valio Aimo API. Runs only when `VALIO_AIMO_API_KEY` (and
`VALIO_AIMO_API_URL`) are set, in the environment or `.env`.
"""

from datetime import date, timedelta

import pytest

from saint_elmo_backend.core.settings import get_settings
from saint_elmo_backend.valio_aimo.client import create_valio_aimo_client
from saint_elmo_backend.valio_aimo.testing import EILA_10L

_settings = get_settings()

pytestmark = pytest.mark.skipif(
    not (_settings.valio_aimo_api_key and _settings.valio_aimo_api_url),
    reason="VALIO_AIMO_API_KEY / VALIO_AIMO_API_URL not set",
)


async def test_ping_and_price_eila_against_the_real_api() -> None:
    client = create_valio_aimo_client(_settings)
    try:
        await client.ping()

        prices = await client.price(
            customer="123",
            requested_date=date.today() + timedelta(days=2),
            products=[EILA_10L],
        )
    finally:
        await client.aclose()

    assert EILA_10L in prices
    assert prices[EILA_10L].product_id == EILA_10L
