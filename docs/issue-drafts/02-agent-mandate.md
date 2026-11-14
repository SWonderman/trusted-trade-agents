# Agent mandate model and read endpoint

## What to build

The mandate data model (design §3.6), seeded for the two demo buyer organisations, plus `GET /api/v1/agents/me/mandate` so an agent can read its own limits and pre-check proposals. Editing mandates is frontend work and not part of this issue.

**Model** (tenant-owned, `org_id` + RLS as in design §3.7; one mandate per agent):

- **Spend:** `maxOrderTotal`, `periodSpendCap` + `spendPeriod` (`WEEK` / `MONTH`), and an optional `categorySpendCaps[{categoryCode, cap}]` per period. EUR, excluding VAT.
- **Assortment:**
  - `allowedCategoryCodes` / `blockedCategoryCodes`
  - `allowedVendors` / `blockedVendors`
  - `allowedCountriesOfOrigin`
  - An empty allow-list means anything is allowed.
- **Requirements:**
  - `requiredClaims[{type, element}]`, `requiredLabels`, `requiredDiets`
  - `excludedAllergens` + `allergenStrictness` (the same values as #4: `contains` / `may_contain` / `declared_free`)
- **Substitution:**
  - `substitutionPolicy`: `NEVER` / `IF_REQUIREMENTS_HOLD` / `ALWAYS_NEEDS_APPROVAL`
  - `maxSubstitutePriceIncreasePct`
- **Delivery:** `laterDeliveryNeedsApproval` (bool) and `minDeliveryReliability` (0–1, nullable).
- **Approval:** `autoApproveUpTo` (order total below which a compliant order needs no human; at most `maxOrderTotal`).

**Endpoint**: `GET /api/v1/agents/me/mandate`, agent scheme only. The principal resolved from the agent key decides the mandate; the client never sends an id.

The response has:

- every field above, with nothing hidden (ADR 0002)
- `agent {id, name}` and `buyerOrganisation {name}`
- `periodSpend {periodStart, periodEnd, committed, remaining}`, computed from orders in `PLACED` / `APPROVED` / `PENDING_APPROVAL` status. This is 0 until draft 06 lands.

**Seed** (dev and demo):

- The hotel chain with agent `dairy-restock`:
  - dairy categories only
  - `requiredClaims [{FREE_FROM, LACTOSE}]`
  - `autoApproveUpTo 1500`, `maxOrderTotal 2000`, `periodSpendCap 5000 / WEEK`
  - `substitutionPolicy IF_REQUIREMENTS_HOLD`
- The hospital kitchen with agent `ward-kitchen`:
  - `excludedAllergens [AM, AW]` with `declared_free`
  - `substitutionPolicy ALWAYS_NEEDS_APPROVAL`
- Each agent has a known dev key printed by the seeder.

Unknown codes in a mandate (category, claim, label, diet, allergen) are rejected when the mandate is written, using the same `UNKNOWN_CODE` validation as #3.

## Acceptance criteria

- [ ] An agent key returns its own mandate and never another agent's (RLS test under two orgs).
- [ ] A user JWT on this route gets 403 `PERMISSION_DENIED`, and no credential gets 401 `INVALID_CREDENTIALS`.
- [ ] `periodSpend` covers the current week or month and is 0 when no orders exist.
- [ ] Both demo organisations and agents are seeded with the values above.
- [ ] Writing a mandate with an unknown code fails with `UNKNOWN_CODE`.
- [ ] The response model is documented in OpenAPI.
