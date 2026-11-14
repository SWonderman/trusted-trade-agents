# Policy engine and reason codes

## What to build

The deterministic policy (design §3.3) that judges a set of priced lines against an agent's mandate and gives a **policy outcome** plus **reason codes**, per line and for the whole basket. It's a pure, internal module with no endpoint. Quotes (05), orders (06) and substitutes (07) call it. The same input always gives the same output, so the audit trail can be replayed.

**Input**:

- the mandate (draft 02)
- the lines: product facts from the catalog, the live offer from draft 03, quantity and line total, and `substitutesFor` if set
- `deliverBy`
- the current period spend
- for substitute lines, the original line's offer

**Output**:

- `outcome`: `AUTO_APPROVE` | `NEEDS_HUMAN` | `REJECT`. The basket outcome is the most severe outcome of any line or basket rule.
- `reasons[{code, severity, lineRef?, message, facts}]`
  - `facts` are the numbers behind the reason, e.g. `{orderTotal: 2140, limit: 2000}`.
  - `message` is one plain-English sentence for approvers.

**Reason code catalogue** (each has a fixed severity):

| Code | Severity | When |
|---|---|---|
| `SALES_BLOCKED` | REJECT | Product or schedule line is sales-blocked |
| `NOT_DELIVERABLE` | REJECT | No schedule line at all |
| `NO_PRICE` | REJECT | Price API returned an error |
| `CLOSING_TIME_PASSED` | REJECT | Cut-off for the date has passed |
| `CONTAINS_EXCLUDED_ALLERGEN` | REJECT | Declared CONTAINS an excluded allergen |
| `MAY_CONTAIN_EXCLUDED_ALLERGEN` | REJECT | With strictness `may_contain` or `declared_free` |
| `ALLERGEN_NOT_DECLARED_FREE` | REJECT | With `declared_free`, no FREE_FROM row (includes UNKNOWN) |
| `BLOCKED_CATEGORY` / `BLOCKED_VENDOR` | REJECT | On a block-list |
| `SUBSTITUTION_NOT_ALLOWED` | REJECT | Substitute line under `NEVER` |
| `OVER_ORDER_LIMIT` | REJECT | Basket total > `maxOrderTotal` |
| `CONVERSION_UNAVAILABLE` | REJECT | Line can't be quantified in the requested unit |
| `CATEGORY_NOT_ALLOWED` / `VENDOR_NOT_ALLOWED` / `ORIGIN_NOT_ALLOWED` | NEEDS_HUMAN | Not on a non-empty allow-list |
| `MISSING_REQUIRED_CLAIM` / `MISSING_REQUIRED_LABEL` / `MISSING_REQUIRED_DIET` | NEEDS_HUMAN | Requirement not declared (unknown counts as missing) |
| `OVER_AUTO_APPROVE_LIMIT` | NEEDS_HUMAN | `autoApproveUpTo` < total ≤ `maxOrderTotal` |
| `OVER_PERIOD_CAP` / `OVER_CATEGORY_CAP` | NEEDS_HUMAN | Period spend + this basket exceeds a cap |
| `PARTIAL_AVAILABILITY` | NEEDS_HUMAN | Known stock < ordered sales units |
| `LATE_DELIVERY` | NEEDS_HUMAN if `laterDeliveryNeedsApproval`, else INFO | Earliest date > `deliverBy` |
| `BELOW_MIN_RELIABILITY` | NEEDS_HUMAN | Reliability < mandate minimum (no data doesn't trigger it) |
| `SUBSTITUTE_NEEDS_APPROVAL` | NEEDS_HUMAN | Substitute line under `ALWAYS_NEEDS_APPROVAL` |
| `SUBSTITUTE_PRICE_INCREASE` | NEEDS_HUMAN | Price per buyer unit up more than `maxSubstitutePriceIncreasePct` |
| `STOCK_UNKNOWN` | INFO | TERMINAL product; quantity can't be confirmed |
| `CONVERSION_UNCERTAIN` | INFO | Cross-check disagreed or was unchecked |
| `ROUNDED_TO_LOT_SIZE` | INFO | Quantity rounded up |

The engine **never reads `buyerRequest` or `rationale`** (ADR 0002).

## Acceptance criteria

- [ ] Table-driven unit tests cover every reason code with its severity, in isolation and in combination.
- [ ] The basket outcome is the most severe line or basket outcome, and a compliant basket under `autoApproveUpTo` is `AUTO_APPROVE` with only INFO reasons.
- [ ] Unknown allergen or claim data is never treated as free-from or as having the claim.
- [ ] Splitting one over-cap order into several smaller baskets in the same period still triggers `OVER_PERIOD_CAP`.
- [ ] Identical inputs give byte-identical outputs (determinism test).
- [ ] The engine has no access to `buyerRequest` or `rationale` (not in its input type).
