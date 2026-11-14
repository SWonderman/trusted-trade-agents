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

## Demo data

`uv run python -m saint_elmo_backend.db.seeders.runner` loads the GS1 code lists, the
catalogue and then two demo buyer organisations (`db/seeders/demo.py`), skipping what is
already there:

| Buyer organisation        | Buyer admin                             | Agent           |
| ------------------------- | --------------------------------------- | --------------- |
| Aurora Hotels             | `buyer.admin@aurora-hotels.example`     | `dairy-restock` |
| Kuusikko Hospital Kitchen | `buyer.admin@kuusikko-hospital.example` | `ward-kitchen`  |

Both buyer admins log in with the dev password `saint-elmo-demo`, which the seeder also
prints. No Agent tokens are seeded. Issue one from the repo root with

```sh
just issue-agent-token dairy-restock buyer.admin@aurora-hotels.example [preset]
```

The preset is `Purchasing` (all scopes, the default) or `"Research only"`, and the token
lasts 30 days. It goes through the same issuance service as the API, records the buyer
admin as its issuer, and is printed once. A buyer admin of another buyer organisation is
refused.

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

## Quotes

`POST /api/v1/quotes` (Agent token, `quote:create`) turns up to 50 lines into a quote:
each line converted and priced through the offers layer, then judged by the policy
(`policy/engine.py`) against the calling agent's mandate. `GET /api/v1/quotes/{quoteId}`
(same scope) reads one back as it was quoted. Both are scoped to the caller's buyer
organisation; another organisation's quote is a 404 `QUOTE_NOT_FOUND`.

- **Created whatever the outcome**: a REJECT is a 201 with its reasons, for the agent to
  revise from and quote again with `previousQuoteId`.
- **`buyerRequest` and `rationale`** are required, stored and echoed, and never read by
  the policy (ADR 0002).
- **Substitutes**: a line with `substitutesFor` is judged by the mandate's substitution
  rules. The substituted product is priced for the same quantity, so prices compare per
  buyer unit. It only has to exist in the catalog.
- **Expiry**: `expiresAt` is the earliest of `createdAt + QUOTE_TTL_MINUTES` (default
  `15`) and each line's offer `validUntil` (its price's `validTo` and closing time for
  `deliverBy`). A deadline that has already passed doesn't count: the policy rejects that
  line (e.g. `CLOSING_TIME_PASSED`), and the quote still starts `QUOTED`. After
  `expiresAt`, `GET` shows `EXPIRED`.
- **Storage**: each quote line keeps its offer as the JSON `POST /offers` returned, and
  the quote keeps the policy reasons, deposits and mandate version in the API's JSON
  shape, so a read shows exactly what the agent was told.
- **Audit**: creating a quote records `QUOTE_CREATED` in `audit_events`
  (`saint_elmo_backend/audit/`). The event holds the full request, every offer used with
  its conversion and provenance (substituted products included), the policy result and
  the mandate version.
- **Period spend** counts the agent's pending, approved and placed orders (below), so the
  period and category caps see them as well as the quote itself.

## Substitutes

`POST /api/v1/products/{code}/substitutes` (Agent token, `offers:read`) ranks substitutes
for a product that can't meet a need, labelled `BEST`, `BETTER`, then `GOOD`. It only
ranks: choosing one and quoting it with `substitutesFor` is the agent's (ADR 0002).
`saint_elmo_backend/substitutes/`.

- **Candidates**: the product's curated substitutes, then products in its category, that
  meet the calling agent's mandate requirements (claims, labels, diets, allergen
  exclusions at the mandate's strictness, allowed origins, minimum reliability) plus the
  request's filters. Required codes are united and origins intersected, so a filter can
  only narrow; disjoint origins find nothing. Blocked categories and vendors are left out,
  since the policy rejects them; ones merely not on the allowed lists stay, with a
  NEEDS_HUMAN `policyPreview`, so a substitute outside the mandate is escalated rather
  than hidden. The mandate's minimum reliability lets
  products without data through, as the policy does; the request's excludes them, as
  search does.
- **Buyer unit**: the request's `unit`, the original's sales unit for a bare `quantity`,
  or without a quantity the original's live comparison unit (L or KG), falling back to its
  sales unit; prices and previews are then for one buyer unit. Candidates whose catalog
  declares no amount in it are dropped before pricing, and those the live conversion
  can't express after.
- **Live offers** are fetched for at most 50 candidates (curated first, then most reliable,
  then by code) plus the original.
- **Ranking** (`substitutes/ranking.py`): a score out of 100. Delivery 40 (20 for meeting
  `deliverBy`, 20 for covering the quantity; unknown stock counts), price per buyer unit 30
  (cheapest candidate's / this one's), reliability 15 (unknown counts as the candidates'
  mean), labels gained 10 (5 each, at most 2), CO₂ estimate 5 (lowest / this one's,
  unknown counts as the mean). Delivery comes first outright: candidates are ordered by
  how many of the two delivery conditions they meet, then by score, so no price
  advantage lifts a late candidate above an on-time one. Ties go to curated substitutes,
  then the lower code.
- **`policyPreview`** judges each candidate as a substitute line for the original, with
  the agent's mandate and period spend, as a quote would now. It commits to nothing.
- Without `deliverBy`, offers are evaluated for tomorrow (Europe/Helsinki), echoed in
  `deliverBy`. No candidates is a 200 with `NO_SUBSTITUTES_FOUND`.
- **Audit**: `SUBSTITUTES_REQUESTED` with the request, the candidates priced, and those
  returned with their ranks, scores and previews.

## Orders

`POST /api/v1/orders` (Agent token, `order:place`) places an order from one of the
agent's own quotes; the Valio Aimo API takes no orders, so they live in Saint Elmo's
order book (`saint_elmo_backend/orders/`). `GET /api/v1/orders` and
`GET /api/v1/orders/{orderId}` read them: an Agent token (`order:read`) sees its own
orders, a user their buyer organisation's. `POST /api/v1/orders/{orderId}/approve` and
`/reject` take a user session only: an Agent token is refused whatever its scopes.

- **Idempotent per quote**: the quote id is the key. A second order from the same quote is
  409 `QUOTE_ALREADY_ORDERED` with `details.orderId`, checked before expiry so a late retry
  still finds its order. An expired quote is 409 `QUOTE_EXPIRED`.
- **Live re-check**: placing re-prices every quote line with `use_cache=False` and judges it
  through the same `policy/assessment.py` as a quote, against the current mandate and
  period spend. AUTO_APPROVE → CONFIRMED → PLACED, NEEDS_HUMAN → PENDING_APPROVAL (with
  `checkAgainAfterSeconds`, 30), REJECT → REJECTED (a 201). `changes` lists where the live
  unit price, available amount, earliest date, closing time or sales block differ from the
  quote's. If the Valio Aimo API is unavailable, placing answers 503 and creates no order,
  so the quote can still be ordered once the API is back.
- **Approval** re-checks once more, without counting the order against its own period
  spend. The NEEDS_HUMAN reasons (by code and line) and the total the order was pending
  with are what the approver accepts. A REJECT reason (e.g. `CLOSING_TIME_PASSED`) rejects it; a
  NEEDS_HUMAN reason it wasn't pending with, or a total above the one it was pending
  with, keeps it PENDING_APPROVAL, showing them, to be decided again (an approval never
  commits more than the approver saw); otherwise it is APPROVED and PLACED. The order
  shows the latest re-check.
- **Status history**: each step with its time and `by`, whoever's request led to it:
  `agent:<name>` on placing, `user:<first and last name>` on approving or rejecting
  (including a rejection by the approval re-check). Only placing a confirmed or approved
  order is `system`.
- **Audit**: `ORDER_REQUESTED`, `ORDER_RECHECKED` (offers, policy, changes; on approval
  also the approver, note and any unseen reasons) on placing and approving, then one
  `ORDER_<STATUS>` per status entered. A human approval is `ORDER_APPROVED` and a human
  rejection `ORDER_REJECTED_BY_HUMAN`; both, and a rejection by the approval re-check,
  carry the approver and note.
- **Period spend** is summed from the order book in `mandates/crud.py`, which reads only
  the orders' tables, so `mandates` never depends on the order services.
- **Tests**: `FakeValioAimoApi.change_price` and `change_availability` move live data
  between a quote and its order.
