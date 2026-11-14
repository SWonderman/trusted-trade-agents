# Quotes

## What to build

`POST /api/v1/quotes` turns an agent's basket into a **quote**: each line converted (draft 03's normaliser), priced from live offers, and judged by the policy (draft 04). The quote expires. `GET /api/v1/quotes/{quoteId}` reads one back. Agent scheme. Quotes are tenant-owned (RLS).

**Request**

- `deliverBy`: ISO date.
- `lines` (1–50): `{productCode, quantity, unit?, substitutesFor?}`. `substitutesFor` is the product code this line replaces; the policy then applies the substitution rules.
- `buyerRequest`: string, required, ≤ 2,000 characters. The need as the buyer stated it.
- `rationale`: string, required, ≤ 2,000 characters. Why the agent chose these lines.
- `previousQuoteId` (optional): the quote this one revises, so a chain of attempts for one buyer request stays connected.

**Response** (201)

- Identity and timing: `quoteId`, `status: "QUOTED"`, `createdAt`, `expiresAt`, `deliverBy` (echoed).
- `lines[]`: product, name, the full `quantity` block from draft 03 (requested → conversion → sales units → delivered → line total), offer price and availability, `substitutesFor`, and the reasons for that line.
- `totals {net, gross, currency}`, plus `deposits` listed separately when present.
- `policy {outcome, reasons[]}` from draft 04: what `place_order` would do if live data hasn't changed.
- `buyerRequest`, `rationale` and `previousQuoteId`, all echoed.

**Rules**

- `expiresAt` is the earliest of:
  - the soonest `validTo` of any line price
  - the soonest `closingTime` for `deliverBy` of any line
  - `createdAt` + TTL (configurable, default 15 min)
- A quote whose outcome is `REJECT` is still created and returned (201). The agent learns why and revises; nothing is an error.
- `GET` after expiry returns the quote with `status: "EXPIRED"`.
- Unknown product codes → 404 `PRODUCT_NOT_FOUND` (all listed). A `substitutesFor` code not among the products the agent has seen is still allowed; it only has to exist in the catalog.

**Audit**: records `QUOTE_CREATED` with the full request, conversions, offers used (with provenance) and the policy result.

## Acceptance criteria

- [ ] The milk example (`463038`, `1000 L`, `deliverBy` a Monday) for `dairy-restock` returns 50 KI and a total. The outcome is `AUTO_APPROVE` or `NEEDS_HUMAN` / `OVER_AUTO_APPROVE_LIMIT` depending on the faked price.
- [ ] A line with `PARTIAL_AVAILABILITY` or `LATE_DELIVERY` carries the shortfall in its reasons with the numbers (available vs ordered, earliest date vs `deliverBy`).
- [ ] A line with `substitutesFor` is judged by the substitution rules. Under the hospital mandate it gives `SUBSTITUTE_NEEDS_APPROVAL`.
- [ ] A `REJECT` quote is created with status 201 and its reasons.
- [ ] `expiresAt` is the earliest of price validity, closing time and TTL. After it passes, `GET` shows `EXPIRED`.
- [ ] Missing `buyerRequest` or `rationale` → 422. Neither value changes the policy result (same quote with different text → same outcome).
- [ ] Agents can't read other organisations' quotes (RLS test). The endpoints are documented in OpenAPI.
