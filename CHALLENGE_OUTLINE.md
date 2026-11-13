# Valio Aimo × Junction 2026 — Challenge Outline

Sources: [project-description.md](project-description.md), [openapi.json](openapi.json), [data/readme.md](data/readme.md), [data/valio_aimo_junction26_product_data_schema.json](data/valio_aimo_junction26_product_data_schema.json), and profiling of the three data files.

## 1. The problem in one sentence

Define the interface and operating model through which an _external_ autonomous purchasing agent (e.g. a hotel chain's agent) can find products, get fixed prices and availability, and place orders with Valio Aimo, **within an explicit mandate** and with human sign-off where needed. It should be built on open standards and must not expose real systems or confidential data.

What we are not asked to build: the B2B marketplace itself, or a chatbot that replaces the webshop UI. We are mocking _today's_ webshop and backend.

Reference request to demo end to end:

> "I need 1,000 litres of lactose-free milk by Monday. Find an option that meets our requirements based on price and availability."

## 2. Scope

### Core (must have)

1. **Product, price and availability lookup**: structured search and retrieval for an agent.
2. **Inquiry → order**: request price and availability, then commit to an order at **fixed prices** (no negotiation).
3. **Permissions and human approval**: what the agent may decide alone vs. what goes to a human.

### Optional (not required to win, but they feed the scoring)

- Delivery time and **sustainability** comparison (delivery reliability, certificates and labels; category CO₂ ranges as a stretch goal).
- **Substitution and exception handling** (partial availability, stock-outs).
- **Traceability and explainability**: a human-readable log of what the agent did and why.

### Problems the sponsor explicitly wants tackled

| Theme            | Question                                                                                                         |
| ---------------- | ---------------------------------------------------------------------------------------------------------------- |
| Trust protocol   | Minimum data and verification needed for an agent to trust stock, price and origin claims without a manual check |
| Guardrails model | Which decisions need sign-off (spend threshold, substitutions outside preferences) vs. fully autonomous          |
| Response logic   | Partial availability, plus "good / better / best" substitution ranking within Aimo's assortment                  |
| Audit trail      | A log both the buyer and Valio Aimo can read                                                                     |

### Scenario menu (pick 1–2 beyond the milk example)

Need → recipe → order · last-minute event · supplier stock-out · proactive selling agent · **allergen-safe substitution (school or hospital)** · standing-order drift detection.

## 3. Judging criteria and what each one implies

| Weight  | Criterion                     | What it means for us                                                                                                            |
| ------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **30%** | Working end-to-end demo       | A full request → lookup → order _or_ approval flow against the **mock API**. Isolated pieces score poorly. This is priority #1. |
| 20%     | Solving the user need         | Precise matching of the request (quantity/unit conversion, "lactose-free", the deadline) with minimal manual correction.        |
| 20%     | Autonomy and controls         | A clear, explicit guardrail model (mandate/policy), an approval flow, and an auditable decision log.                            |
| 15%     | Robustness to exceptions      | Partial availability, substitutions, delivery deadlines that can't be met. Show beyond the happy path.                          |
| 15%     | Openness / path to production | Open, documented standards (OpenAPI, MCP, JSON Schema, GS1, VCs…), stated assumptions, justified choices, next steps.           |

## 4. Resources we have

### 4.1 What is in `data/` (static, synthetic)

| File                                             | Size                       | Content                                                                                                       |
| ------------------------------------------------ | -------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `valio_aimo_junction26_product_data.json`        | 87 MB, **17,546 products** | Catalog: units, lot size, category, vendor, origin, substitutions, deposits, and GS1 Synkka manufacturer data |
| `valio_aimo_junction26_product_data_schema.json` | —                          | JSON Schema (2020-12) for the above, well documented                                                          |
| `valio_aimo_junction26_delivery_reliability.csv` | 4,425 rows                 | `productId, deliveryReliability` (0–1, delivered vs. ordered quantity)                                        |
| `valio_aimo_junction26_carbon_footprint.csv`     | 11,033 rows                | `productId, AVG kg CO2-eq/kg`: a **product-group average**, not per product                                   |

All three share the same product `id` (e.g. `463038`), which is also the id used by the API.

### 4.2 Mock API ([openapi.json](openapi.json), OpenAPI 3.1, v0.1.0)

Auth: header `X-API-Key`. **The spec has no `servers` entry**, so the base URL comes from the portal.

| Endpoint                                                                                             | Purpose                                                            |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `GET /api/ping`                                                                                      | Health and auth check                                              |
| `POST /api/availability`                                                                             | Whether products can be delivered on a date, and how much          |
| `POST /api/price`                                                                                    | Price per sales unit for a delivery date                           |
| `GET /api/products/download`, `/api/delivery-reliability/download`, `/api/carbon-footprint/download` | Redirects to the same static files already in `data/` (fetch once) |

**Request (both on-demand endpoints):** `{ "customer": "123", "requestedDate": "2026-11-16", "products": ["460013", …] }`. Up to **1,000 product ids** per call; more returns HTTP 422. The `customer` value is ignored in the mock (any string works), but in reality prices and stock are customer-specific.

**Availability response**, per product:

- `salesBlock`: the product can't be ordered right now (at product level and per schedule line).
- `logisticModel`:
  - **Stock**: Aimo's own warehouse, so the quantity shown is real.
  - **Terminal**: shipped from the supplier's warehouse. Quantity is unknown and always reported as `999999`.
- `closingTime`: the order cut-off for receiving goods on `availableDate`.
- `scheduleLines`:
  - **Empty array**: the product can't be delivered on any date.
  - **Otherwise exactly one line** with `availableAmount` (in the **sales unit**; 0 means unavailable), `availableDate` (the earliest date, **which may be later than the requested date**), and `salesUnit`.

**Price response**, per product (all prices are **per one sales unit**, `quantity` is always 1.0):

- `catalogPrice` (value with and without tax)
- `listPrice`: the price before any customer-specific discount
- `netPriceFound`: whether a customer-specific price was applied
- `priceWithTax`
- `comparisonPrice` + `comparisonUnit`, per **KG or L**. **This solves the litres problem**: price per litre comes straight from the API, and the litres in one sales unit ≈ `catalogPrice / comparisonPrice`.
- `tax.taxRate`: the authoritative VAT rate
- `validFrom` / `validTo`: when the price applies
- `error: true`: no price was found for this product

**Usage rules (they matter for both scoring and design):**

- **Don't poll prices or availability for the whole catalogue.** First narrow the candidates using the static data, then query only those.
- **The API has rate limits it doesn't publish.** So: search locally, query the API in batches, and cache responses within the price validity window.

### 4.3 What does NOT exist anywhere, so we build it ourselves

- **No order, cart, quote or approval endpoint.** The mock API is read-only. Placing orders, approval, customer mandates and the audit log **all have to be built (mocked) by us**. That is the actual "interface + operating model" the challenge asks for. The order step must re-check price and availability at commit time against `closingTime`.
- **Webshop test accounts** (to be shared later; not needed for the core flow).
- **Code → name lookups** that are deliberately missing: category names (349 codes), unit codes (`KI`, `ST`, `PAK`…), `temperatureCondition` codes, fishing area and method codes, hazard codes.

## 5. Data facts that matter for the design

**Catalog shape**

- 648 vendors (Duni, Valio, Atria, HKFoods…); 349 category codes; origin mostly `fi` (≈45%), then de/it/se/cn/nl.
- Names are in **fi (100%), en (≈100%), sv (92%)**, so English search works.
- **Sales unit ≠ base unit.** Top sales units: `KI` 8,005, `ST` 5,607, `KG` 1,068, `PAK`, `BAG`, `RAS`, `PRK`, `BOT`, `SK`… The `units[]` array gives `sizeInBaseUnits`. Example: `463038` _Valio Eila® semi skimmed milk drink 10 l novobox lactose free_ is sold per `KI` = 2 × `ST`, so one sales unit is about 20 L and 1,000 L means 50 sales units. The static data has no direct litres/kg per sales unit, but the price API's `comparisonPrice` (per L/KG) lets us derive it (`catalogPrice / comparisonPrice`). Cross-check it against the product name and `unitConversions`. This is a key "precision" risk, so show the conversion to the buyer.
- `allowedLotSize`: 96% have `0.01` (effectively free quantity); the rest need multiples (2, 3, 1.5, 5, 10…). Order validation must enforce this.
- `deposits` (returnable packaging) on 506 products are charged in addition to the product price.
- `variableUnit` marks products sold by variable weight.

**Dietary, allergen and sustainability signals (in `synkkaData.classifications`)**

- `allergen`: GS1 codes with `CONTAINS` / `MAY_CONTAIN` (e.g. `AM` milk, `AW` gluten cereals, `UW` wheat, `AE` egg, `AN` tree nuts, `AY` soy). `nonAllergen` gives `FREE_FROM`. Needed for **allergen-safe substitution**.
- `nutritionalClaim`: `FREE_FROM_LACTOSE` (4,178 products), `LOW_LACTOSE` (321), `FREE_FROM_GLUTEN`, `VEGAN`, `VEGETARIAN`… Structured filters for requests like "lactose-free".
- `packagingMarkedLabel`: certificates and labels such as `EU_ORGANIC_FARMING` (456), `SVANEN`, `RAINFOREST_ALLIANCE`, `MSC`, `ASC`, `FAIR_TRADE_MARK`, `KRAV`, Finnish origin marks (Blue Swan, Made in Finland key flag), the Heart Symbol (a health mark), and **temperature class** (`warm/cool/freezeTemperature`), which lets us decode `temperatureCondition`.
- `nutritionalContent`, `ingredients` (with origins per production stage), `fishingReports`, `producers` (GLN), and `brand` are useful for origin and traceability claims.
- **Data quality varies by design.** Only ~82% have a GTIN or brand, 70% have nutrition data, and 21% have structured ingredients. Fresh produce is the sparsest. The agent must treat "unknown" as different from "free from".

**Substitutions**

- Only **189 products / 250 rules** have curated substitutes, mostly fresh produce (e.g. Dutch ↔ Finnish tomato and cucumber). For anything else we need **our own substitution ranking**: same category + required claims and allergens + unit compatibility, ranked good/better/best by price, reliability, CO₂ and labels.

**Delivery reliability** (25% coverage)

- Mean 0.972, median 1.0; 1,935 products < 1.0 and **291 < 0.9**. Use it as a risk score in offer ranking and as an approval trigger.

**Carbon footprint** (63% coverage)

- Range 0.13–30.46 kg CO₂-eq/kg, median 2.11, only 177 distinct values, because these are category averages. Present them as an _estimate range_, never as a product-level claim, because the trust protocol must be honest about this.

## 6. Actors and trust model (design principles)

```
Buyer's agent (untrusted)  →  Our gateway ("Aimo's side")  →  Mock API + static data (Aimo's backend)
                                   ↓
                      Human approver (buyer org)
```

- **Buyer's agent**: an outside party acting for a professional kitchen (hotel chain, school, hospital). It does almost all of the "agent" work in the brief's scenarios (search, compare, order, substitutions, last-minute events, stock-outs). It is our demo client, not the product.
- **Our gateway (Aimo's side)**: the system built in this challenge. It sits in front of the mock API and adds the agent interface, the mandate and policy engine, ordering, the approval queue and the audit log.
- **Mock API + static data**: stands in for Aimo's real backend (catalogue, pricing, stock).
- **Human approver**: a person at the buyer organisation who sets up the mandate and signs off escalated orders.
- **Aimo's own agent** (optional): appears only in the "proactive selling" scenario, where it pushes suggestions to the buyer's agent.

**Zero trust toward the buyer's agent:**

1. **The mandate is not set by the agent.** A human at the buyer organisation registers it once with the gateway: spend limits, allowed categories and vendors, required claims and allergen exclusions, substitution rules, approval thresholds. The agent's credential is bound to that mandate. Anything the agent claims about its own authority is ignored.
2. **The gateway enforces everything deterministically.** Every quote and order is re-checked by plain code, not by a language model: mandate, minimum order step, live price and availability, and `closingTime`. Each check produces a reason code. Nothing the agent writes can talk its way past a rule, and the audit log is reproducible.
3. **Approval goes through a separate channel.** Orders that need sign-off go to the human through an approval UI or notification, never back through the agent's connection. The agent only sees `pending_approval` and then `approved` or `rejected`, so it cannot approve its own orders.
4. **Everything is re-checked at commit.** Quotes expire. When an order is placed, the gateway re-fetches price and availability, so nothing is confirmed at a stale price, after the cut-off, or beyond the available stock.
5. **Least privilege.** Credentials are scoped, rate limits are enforced, and the agent sees only its own customer's prices and orders. Internal systems are never exposed directly.
6. **Buyer-side guardrails are convenience, not security.** The agent can pre-filter options so it doesn't propose orders that will be rejected, but the gateway is the single point of enforcement.

**Verifiable claims, in the other direction (the trust protocol):** the buyer's agent shouldn't blindly trust Aimo either. Every price, stock figure, origin claim and label carries where it came from, when, how long it's valid, and how certain it is. Examples:

- Stock quantity: "Stock" products report a real quantity; for "Terminal" (supplier-shipped) products the `999999` is replaced by "unknown".
- Labels and allergens: say whether they come from the manufacturer's data (Synkka) or are missing.
- CO₂: marked as an average for the product group.

Optionally, offers can be signed (JWS or W3C Verifiable Credentials) so the agent can verify them without a manual check.

## 7. Building blocks of a solution (suggested shape)

Data flow: **static catalogue (local index) → narrow down the candidates → `/api/price` + `/api/availability` (batched, cached) → rank → our own order/approval service → audit log.**

1. **Agent-facing interface (the "front door")**
   - OpenAPI-described REST plus an **MCP server** wrapping it (tools: `search_products`, `get_offer` (price + availability + delivery date), `create_quote`/`reserve`, `place_order`, `request_approval`, `get_audit_log`).
   - Responses use **open vocabularies**: GS1 (GTIN, allergen codes, packaging levels) and schema.org `Product`/`Offer`/`Order`, with JSON Schema for everything.
   - Explicit **quantity normalisation** (requested litres/kg → sales units → lot-size rounding), with the conversion shown in the response.
2. **Trust layer**: every claim (price, stock, origin, certificate) carries provenance: source system, timestamp, validity window (`priceValidUntil`), and the data source (Synkka vs. category estimate). Optionally sign offers (JWS / W3C Verifiable Credentials) so the buyer agent can verify them without a manual check.
3. **Guardrails / mandate model**: a machine-readable buyer **mandate** per agent: spend limit per order, per period and per category; allowed vendors and origins; mandatory claims (lactose-free, allergen exclusions); substitution policy; delivery deadline. A deterministic **policy engine** decides `auto-approve` / `needs-human` / `reject`, with the reason codes.
4. **Exception logic**: partial availability → split (partial fill + substitute + later delivery) → ranked alternatives (good/better/best) → escalate when the substitute is outside the mandate.
5. **Human approval loop**: a small UI or notification where the buyer approves or rejects a pending order with the agent's explanation.
6. **Audit trail**: an append-only, human-readable event log (request → search → offers compared → policy decision → approval → order), visible to both buyer and Valio Aimo. Optionally hash-chained.

## 8. Open questions to clarify with mentors or the portal

- What is the API base URL (it's missing from the spec), and what are the rate limits in practice?
- Is the absence of an order endpoint intentional, i.e. teams mock order placement themselves? Is any specific order format expected (e.g. an existing webshop or EDI order structure)?
- Is availability deterministic, and does it change during the event, so a stock-out demo is reproducible? How often do Terminal products (unknown quantity) appear?
- Meanings of the unit codes (`KI`, `PAK`, `RAS`, `SK`, `KLE`…) and `temperatureCondition` codes; category names.
- Is `closingTime` the only cut-off rule, or are there delivery weekdays per customer? (What does "by Monday" resolve to?)
- Is there a notion of a customer's assortment, contract, or standing order? (It isn't in the API.)

## 9. Suggested priorities for the hackathon

1. **Get the mock API working first** (`/api/ping` with the key) and build the thin agent interface over it, plus our own order and approval service (the mock has none). This unlocks the 30% criterion.
2. Nail the **milk example precisely**: unit conversion, lactose-free filter, deadline check, price comparison, and an order or approval at the threshold.
3. Add the **mandate and policy engine plus audit log** (20%), with clear reason codes.
4. Add **one exception scenario** end to end: partial availability → ranked substitute → human approval (15%).
5. Write up the **standards and assumptions** page and next steps (15%).
