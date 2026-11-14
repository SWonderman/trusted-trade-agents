"""
In-process cache of Valio Aimo API answers, keyed by customer number, product code and
delivery date.

A price is reused while it is within its own `validFrom`/`validTo` window. Availability
moves faster, so it is reused only for a short, configurable time (default 60 s).
Failed lookups (`error: true`, products the API left out) are never cached.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from saint_elmo_backend.offers.timestamps import parse_timestamp
from saint_elmo_backend.valio_aimo.schemas import ProductAvailability, ProductPrice

DEFAULT_AVAILABILITY_TTL = timedelta(seconds=60)
# Expired entries are swept once the cache holds more than this many
_SWEEP_THRESHOLD = 10_000

type CacheKey = tuple[str, str, date]


@dataclass(frozen=True, slots=True)
class Cached[T]:
    value: T
    fetched_at: datetime
    expires_at: datetime


class OfferCache:
    def __init__(self, availability_ttl: timedelta = DEFAULT_AVAILABILITY_TTL) -> None:
        self._availability_ttl: timedelta = availability_ttl
        self._prices: dict[CacheKey, Cached[ProductPrice]] = {}
        self._availability: dict[CacheKey, Cached[ProductAvailability]] = {}

    def get_price(
        self, customer: str, product: str, on: date, now: datetime
    ) -> Cached[ProductPrice] | None:
        return _fresh(self._prices, (customer, product, on), now)

    def put_price(
        self, customer: str, product: str, on: date, price: ProductPrice, fetched_at: datetime
    ) -> None:
        """
        Kept only while `fetched_at` lies within the price's validity window.
        """
        if price.error or price.catalog_price is None:
            return
        valid_from = parse_timestamp(price.catalog_price.valid_from)
        valid_to = parse_timestamp(price.catalog_price.valid_to)
        if valid_from is None or valid_to is None or not valid_from <= fetched_at < valid_to:
            return
        _put(self._prices, (customer, product, on), Cached(price, fetched_at, valid_to), fetched_at)

    def get_availability(
        self, customer: str, product: str, on: date, now: datetime
    ) -> Cached[ProductAvailability] | None:
        return _fresh(self._availability, (customer, product, on), now)

    def put_availability(
        self,
        customer: str,
        product: str,
        on: date,
        availability: ProductAvailability,
        fetched_at: datetime,
    ) -> None:
        entry = Cached(availability, fetched_at, fetched_at + self._availability_ttl)
        _put(self._availability, (customer, product, on), entry, fetched_at)


def _fresh[T](store: dict[CacheKey, Cached[T]], key: CacheKey, now: datetime) -> Cached[T] | None:
    entry = store.get(key)
    if entry is None:
        return None
    if now >= entry.expires_at:
        del store[key]
        return None
    return entry


def _put[T](
    store: dict[CacheKey, Cached[T]], key: CacheKey, entry: Cached[T], now: datetime
) -> None:
    if len(store) >= _SWEEP_THRESHOLD:
        for stale in [k for k, e in store.items() if now >= e.expires_at]:
            del store[stale]
    store[key] = entry
