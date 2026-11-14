# Orders, approval and order status

## What to build

Placing an order from a quote, the human approval step, and status polling, following the lifecycle in design §3.5. The mock Valio Aimo API has no order endpoint, so orders live in our own order book.

**`POST /api/v1/orders`** (agent scheme). Body: `{quoteId}`.

1. Reject if the quote is expired (409 `QUOTE_EXPIRED`) or already ordered (409 `QUOTE_ALREADY_ORDERED`; `details` carries the existing `orderId`). **The quote id is the idempotency key**, so a retry can never create a second order (ADR 0002).
2. **Re-check live**: fetch fresh offers for every line (bypassing the cache), re-run the conversion and the policy with the current period spend.
3. Outcome:
   - `REJECT` → order `REJECTED`
   - `NEEDS_HUMAN` → `PENDING_APPROVAL`
   - `AUTO_APPROVE` → `CONFIRMED`, then immediately `PLACED`
4. If live prices or availability changed from the quote, the order still follows the new policy result. The response lists what changed (`changes[{lineRef, field, quoted, now}]`).

Response (201): the order with:

- `orderId`, `quoteId`, `status`
- `lines`, `totals`, `policy {outcome, reasons}`, `changes`
- `checkAgainAfterSeconds` (only when `PENDING_APPROVAL`; e.g. 30)

A `REJECTED` order is a 201 with reasons, not an error.

**`GET /api/v1/orders/{orderId}`** and **`GET /api/v1/orders`** (agent: own orders only; user: their organisation's orders).

- The list returns the most recent first, with an optional `status` filter, paginated.
- Each order includes:
  - its status history (`[{status, at, by: "agent:<name>" | "user:<name>" | "system"}]`)
  - the approver's note when decided
  - `checkAgainAfterSeconds` while pending

**`POST /api/v1/orders/{orderId}/approve`** and **`/reject`** (**user scheme only**; an agent key gets 403 `PERMISSION_DENIED`). Body: `{note?}`.

- Approve re-checks live data once more:
  - if it passes (excluding the NEEDS_HUMAN reasons the human just accepted), → `APPROVED` → `PLACED`
  - if a REJECT reason now applies (e.g. closing time passed), → `REJECTED` with that reason
- Only `PENDING_APPROVAL` orders can be decided (409 `ORDER_NOT_PENDING` otherwise).

**Period spend**: `PENDING_APPROVAL`, `APPROVED` and `PLACED` orders count toward the mandate's period spend (draft 02).

**Audit**: `ORDER_REQUESTED`, `ORDER_RECHECKED` (with changes), `ORDER_<STATUS>` and `ORDER_APPROVED` / `ORDER_REJECTED_BY_HUMAN` (with the approver and note).

## Acceptance criteria

- [ ] Ordering a compliant, unexpired quote gives `PLACED`. An over-auto-approve quote gives `PENDING_APPROVAL` with `checkAgainAfterSeconds`.
- [ ] Posting the same `quoteId` twice gives 409 `QUOTE_ALREADY_ORDERED` with the first `orderId`, and only one order exists.
- [ ] An expired quote gives 409 `QUOTE_EXPIRED`.
- [ ] The re-check uses fresh Valio Aimo data. A changed price or availability shows up in `changes` and can change the outcome.
- [ ] An agent key can't approve or reject (403). A user can, and approval re-checks; past the closing time it ends `REJECTED` with `CLOSING_TIME_PASSED`.
- [ ] `GET /orders` returns only the caller's orders (RLS test) with full status history.
- [ ] Pending orders count toward period spend: a second order that pushes past the cap gets `OVER_PERIOD_CAP`.
- [ ] All endpoints and errors are documented in OpenAPI.
