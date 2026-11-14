# Live offers with quantity conversion

## What to build

`POST /api/v1/offers`: live price and availability from the Valio Aimo API for a shortlist of products on a delivery date. If the agent gives a quantity in buyer units, the response also converts it to sales units and prices the line. This is what lets an agent rank "best by price for 1,000 L by Monday" before building a quote. There's no policy here: an offer is binding on nothing.

**Request**

- `deliverBy`: ISO date, resolved by the agent (ADR 0002).
- `items` (1–50): `{productCode, quantity?, unit?}`. `unit` is `L`, `KG`, or a sales unit code such as `KI`/`ST`. With no unit, the quantity is in the product's sales unit.

**Behaviour**

- Calls `/api/price` and `/api/availability` for the listed products only, batched, with `requestedDate = deliverBy` and `customer` = the buyer organisation's Valio Aimo customer number.
- Responses are cached per customer number + product + date, **within the price's `validFrom`/`validTo` window**. Availability is cached briefly (configurable, default 60 s). Rate limits get retry with backoff.
- **Quantity normaliser** (shared with draft 05):
  - For `L`/`KG`, the amount per sales unit is `catalogPrice / comparisonPrice`. It is cross-checked against the product's `units[]`/`unitConversions` and the size in the product name.
  - The quantity is rounded **up** to whole sales units and then to the lot size.
  - If the amount can't be established, the line is still returned with reason code `CONVERSION_UNAVAILABLE` and no line total.

**Response**: `deliverBy` (echoed), `evaluatedAt`, and per item:

- Product: `productCode`, `name`, `salesUnit`.
- `price`:
  - `perSalesUnit {net, gross}`, `taxRate`, `currency: "EUR"`
  - `comparisonPrice {value, unit}`
  - `customerSpecific` (= `netPriceFound`), `validFrom`, `validTo`
- `availability`:
  - `logisticModel` (`STOCK` / `TERMINAL`)
  - `availableAmount`: **null for TERMINAL**, replacing the API's `999999`, with `availableAmountKnown: false`
  - `earliestDate`, `closingTime`, `salesBlocked`, `meetsDeadline` (earliest date ≤ `deliverBy` and closing time not passed)
- `quantity` (only when a quantity was given):
  - `requested {value, unit}`
  - `conversion {perSalesUnit {value, unit}, basis: "PRICE_COMPARISON", crossCheck: "AGREES" | "DISAGREES" | "UNCHECKED"}`
  - `salesUnits`, `lotSize`, `roundedUp`
  - `delivered {value, unit}`: what the buyer actually gets in buyer units
  - `lineTotal {net, gross}`
  - `coveredByAvailability` (true, false, or null when the amount is unknown)
- Product facts: `deliveryReliability`, `carbonFootprint` (with basis, as in #2).
- `reasonCodes`: shortfall and data codes from draft 04's catalogue, e.g. `PARTIAL_AVAILABILITY`, `LATE_DELIVERY`, `NOT_DELIVERABLE`, `SALES_BLOCKED`, `NO_PRICE`, `CLOSING_TIME_PASSED`, `CONVERSION_UNAVAILABLE`, `CONVERSION_UNCERTAIN`.
- `provenance`: the source (Valio Aimo price/availability API), `fetchedAt`, `validUntil`, and `cached` (bool).

Unknown product codes → 404 `PRODUCT_NOT_FOUND`, listing every unknown code. More than 50 items → 422.

## Acceptance criteria

- [ ] The milk example works with a faked Valio Aimo API: product `463038` with `1000 L` gives a conversion of about 20 L per KI, 50 KI, and the line total. The cross-check agrees with the product name.
- [ ] Quantities round up to whole sales units and the lot size, and `roundedUp` / `delivered` reflect it.
- [ ] TERMINAL products return `availableAmount: null` and `coveredByAvailability: null`, never 999999.
- [ ] An earliest date later than `deliverBy` gives `meetsDeadline: false` and `LATE_DELIVERY`. Empty schedule lines give `NOT_DELIVERABLE`.
- [ ] A price `error: true` gives `NO_PRICE` and no line total, without failing the other items.
- [ ] A second identical request within the price validity window makes no new Valio Aimo price call (`cached: true`).
- [ ] Only the requested products are sent to the Valio Aimo API, batched.
- [ ] Unknown product codes return 404 listing all of them. The endpoint and its errors are documented in OpenAPI.
