# Ranked substitutes

## What to build

`POST /api/v1/products/{code}/substitutes`: when a product can't meet the need (a shortfall in an offer or quote), the agent asks for ranked **substitutes** labelled best / better / good. The backend reads the requirements from the agent's own mandate, so the agent can tighten them but never loosen them. The backend only ranks; picking one and re-quoting is the agent's decision (ADR 0002). Agent scheme.

**Request** (all optional):

- `quantity` + `unit`, and `deliverBy`: when given, candidates are judged on whether they can cover that quantity by that date.
- Tightening filters, using the same names and validation as #3/#4: `requiredClaims`, `requiredLabels`, `requiredDiets`, `excludedAllergens`, `countriesOfOrigin`, `minDeliveryReliability`. These are **added to** the mandate's requirements, never instead of them.
- `limit` (default 3, max 10).

**Candidate generation** (deterministic):

1. The product's curated substitutes (#5).
2. Products in the same category that pass the mandate's requirements and the tightening filters (via #3/#4 search), and can be expressed in the same buyer unit (both convertible to L, or both to KG, or the same sales unit).
3. Capped at 50 candidates, then live offers fetched (draft 03) only for those.

**Ranking**: candidates are scored on these inputs, in this order of importance:

1. meets `deliverBy` and covers the quantity
2. price per buyer unit (comparison price)
3. delivery reliability (no data counts as neutral, not bad)
4. labels gained
5. CO₂ estimate (lower is better)

The weights are documented. The top results are labelled `BEST`, `BETTER`, `GOOD` in rank order (beyond 3: `GOOD`).

**Response**: `original {productCode, name, offer}`, `deliverBy` (echoed), and `candidates[]`. Each candidate has:

- `rank`, `tier`, `curated` (bool)
- `productCode`, `name`, `offer` (draft 03's shape, including `quantity` when given)
- `tradeOffs` against the original:
  - `pricePerBuyerUnitDeltaPct`
  - `earliestDateDelta`
  - `reliabilityDelta`
  - `claimsKept[]` / `claimsLost[]`, `labelsGained[]` / `labelsLost[]`
  - `carbonFootprintDelta` (marked as a product-group estimate)
- `policyPreview {outcome, reasons}`: draft 04 run on this candidate as a substitute line for the original. This shows the agent up front whether choosing it would need approval. It's a preview, not a commitment.

Unknown `code` → 404 `PRODUCT_NOT_FOUND`. Unknown codes in filters → 422 `UNKNOWN_CODE`. No candidates → 200 with empty `candidates` and reason code `NO_SUBSTITUTES_FOUND`.

**Audit**: `SUBSTITUTES_REQUESTED` with the candidates returned and their ranks.

## Acceptance criteria

- [ ] Curated substitutes appear first among equally eligible candidates and are marked `curated: true`.
- [ ] Every candidate meets the mandate's requirements. For the hospital agent, no candidate CONTAINS `AM` or `AW` or lacks a FREE_FROM declaration for them.
- [ ] Tightening filters narrow the results. There is no parameter that can drop a mandate requirement.
- [ ] Candidates that can't be expressed in the requested buyer unit are excluded.
- [ ] Ranking is deterministic and follows the documented order. Tiers are BEST / BETTER / GOOD.
- [ ] `policyPreview` shows `SUBSTITUTE_NEEDS_APPROVAL` under `ALWAYS_NEEDS_APPROVAL`, and `SUBSTITUTE_PRICE_INCREASE` when over the mandate's limit.
- [ ] Live offers are fetched only for the capped candidate set.
- [ ] The endpoint and its errors are documented in OpenAPI.
