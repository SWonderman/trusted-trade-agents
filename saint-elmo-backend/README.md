# Saint Elmo backend

## Tests

```sh
cp .env.example .env          # once
docker compose up -d db
uv run pytest
```

Unit tests need nothing else. Integration tests (those using the `client`, `session`,
`clean_db` or `reference_data` fixtures from `conftest.py`) run against a separate
`<POSTGRES_DB>_test` database on the compose Postgres, e.g. `saint_elmo_test`. It is
created and migrated to head automatically on first use, and truncated before each
test, so the seeded dev database is never touched.

- `reference_data` seeds only the GS1 code lists. Insert the products a test needs
  with `catalog/tests/factories.py`, and buyer organisations and users with
  `accounts/tests/factories.py`.

## Valio Aimo API

`saint_elmo_backend/valio_aimo/` is a thin async client for the Valio Aimo API (live
price and availability, `openapi.json` at the repo root): `price`, `availability` and
`ping`. It only talks to the API. Caching and domain rules belong to the offers layer (below).

### Settings

| Variable                          | Default | Meaning                                         |
| --------------------------------- | ------- | ----------------------------------------------- |
| `VALIO_AIMO_API_URL`              | unset   | Base URL from the challenge portal              |
| `VALIO_AIMO_API_KEY`              | unset   | Sent as `X-API-Key`. Never commit it            |
| `VALIO_AIMO_MAX_ATTEMPTS`         | `3`     | Attempts per request in total, first included   |
| `VALIO_AIMO_BACKOFF_BASE_SECONDS` | `0.5`   | First backoff delay; doubles on each retry      |

Both URL and key are optional, so the app starts and catalog-only development works
without them. The first call then raises `ValioAimoNotConfigured`. There is never a
fallback to fake data.

`lifespan` creates one client (one `httpx.AsyncClient`) and closes it on shutdown. Routes
take it as `AValioAimoClient`. Tests override `get_valio_aimo_client` with
`valio_aimo.testing.make_fake_client()`, a real client on top of `FakeValioAimoApi`, which
scripts the scenarios the offers work needs (`463038` with a per-litre comparison price,
TERMINAL, `error: true`, undeliverable, late, sales-blocked, 429 then success). Its
values and formats are copied from live responses: title-case `logisticModel` (`Stock`,
`Terminal`) and timestamps such as `2026-11-16T00:00:00+0200`.

The smoke test in `valio_aimo/tests/test_smoke.py` calls the real API (`ping` plus a
price for `463038`) and runs only when `VALIO_AIMO_API_URL` and `VALIO_AIMO_API_KEY` are
set.

### Assumptions about the API

- **The mock ignores `customer`.** Any string works. Real prices and stock are
  customer-specific, so callers pass the buyer organisation's customer number anyway.
- **`999999` means unknown.** TERMINAL products report it as `availableAmount`. The
  client passes it through unchanged, along with `error: true`, empty `scheduleLines` and
  `salesBlock`. Interpreting them is the caller's job.
- **Prices are per sales unit.** `quantity` is always 1. Litres or kilograms per sales
  unit ≈ `catalogPrice / comparisonPrice`.
- **At most 1,000 product codes per call.** Longer lists are split into batches of
  1,000, sent one after another, and merged. Duplicates are dropped.
- **Rate limits are unpublished.** 429, 5xx, timeouts and connection errors are retried
  with exponential backoff and ±20% jitter (about 0.5 s, then 1 s). A numeric
  `Retry-After` is honoured, but never waits less than the backoff. One over 10 s fails
  the call instead of holding the request open. Other 4xx (401 for a wrong key, 422) fail straight away. If
  any batch still fails, the whole call raises `ValioAimoUnavailable`, never half the
  results.
- **A product the API leaves out is simply absent** from the result mapping.
- **Dates and times stay strings.** The spec doesn't fix their format.

## Offers

`POST /api/v1/offers` (Agent token, `offers:read`) returns live price and availability
for up to 50 products on `deliverBy`, priced for the caller's buyer organisation (its
`customer_number`; the request has no customer field). `saint_elmo_backend/offers/`
interprets the client's raw values: `999999` and TERMINAL become an unknown amount,
`error: true` or a product missing from the price answer becomes `NO_PRICE`, empty
schedule lines or a product missing from the availability answer become
`NOT_DELIVERABLE`.

- **Quantity conversion** (`offers/quantity.py`, reused by quotes): `L`/`KG` per sales
  unit = catalog price / comparison price, cross-checked against the size in the
  product name and the declared packaging (within 5%). When it agrees, the packaged
  amount is used, since the price ratio carries cent rounding (31.31 / 1.57 = 19.94 L
  for a 2 × 10 l case). Quantities round up to whole sales units, then to the lot size.
- **Cache** (`offers/cache.py`, in process): per customer number, product and date. A
  price is reused within its `validFrom`/`validTo`; availability for
  `OFFERS_AVAILABILITY_CACHE_SECONDS` (default `60`). Failed lookups are never cached.
- **Demo flag** `OFFERS_IGNORE_CLOSING_TIME` (default `false`): the live mock ignores
  `requestedDate` and answers a frozen snapshot whose closing times have passed, while its
  `timeNow` is real, so every live offer would carry `CLOSING_TIME_PASSED` (a REJECT in the
  policy). With `true`, a passed closing time is still reported but neither fails
  `meetsDeadline` nor limits `validUntil`. Never enable it against a real system.
- The API still failing after the client's retries, or not being configured, answers
  503 `VALIO_AIMO_UNAVAILABLE`. A buyer organisation without a customer number answers
  409 `CUSTOMER_NUMBER_MISSING`.
