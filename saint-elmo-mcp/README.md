# Saint Elmo MCP server

The way into Saint Elmo for purchasing agents that speak MCP. It's a thin, stateless adapter. Each tool calls one Saint Elmo backend endpoint over HTTP, passing along the caller's agent key, and the backend does all validation, policy, state and audit. Why it's built this way: [ADR 0001](../docs/adr/0001-mcp-server-is-a-thin-stateless-adapter.md).

Built on the official MCP Python SDK v2 (`MCPServer`, which was called `FastMCP` in v1), serving stateless streamable HTTP.

## Tools

| Tool | Backend endpoint | Status |
|---|---|---|
| `get_my_mandate` | `GET /api/v1/agents/me/mandate` (#11) | no parameters (the backend finds the mandate from the agent token); the whole mandate, nothing hidden: `version`, `agent`, `buyerOrganisation`, spend (`maxOrderTotal`, `periodSpendCap`, `spendPeriod` `WEEK` / `MONTH`, `categorySpendCaps`), assortment allow- and block-lists (empty allow-list = anything), requirements (`requiredClaims`, `requiredLabels`, `requiredDiets`, `excludedAllergens`, `allergenStrictness`), substitution (`substitutionPolicy`, `maxSubstitutePriceIncreasePct`), delivery (`laterDeliveryNeedsApproval`, `minDeliveryReliability`), `autoApproveUpTo` and `periodSpend` (`committed`, `remaining`). Errors `MANDATE_NOT_FOUND`, `PERMISSION_DENIED` |
| `search_products` | `POST /api/v1/products/search` (#2, #3, #4) | query, language, paging; filters `categoryCodes`, `vendors`, `requiredClaims`, `requiredDiets`, `requiredLabels`, `countriesOfOrigin`, `minDeliveryReliability`; allergen exclusion `excludedAllergens` + `allergenStrictness` (`contains` / `may_contain` / `declared_free`); per-hit `allergens` status (`UNKNOWN` = no data, not safe) |
| `get_vocabulary` | `GET /api/v1/catalog/vocabulary` (#6) | optional `vocabularies` subset (`claims`, `diets`, `labels`, `allergens`, `categories`), trimmed on the MCP side; per entry GS1 `code`, `name` (null for non-GS1 codes), `definition`, `productCount`; claims as `type` + `element` pairs; allergens with `statusCounts`; categories as code + count only |
| `get_product` | `GET /api/v1/products/{code}` (#5) | `code`, `language`; search summary plus full `allergens` (containment; unlisted = unknown, not safe), `ingredients` with origins, `nutrients`, `packagingLevels`, `deposits`, `producers`, `curatedSubstitutes`, `provenance`. `PRODUCT_NOT_FOUND` for an unknown code |
| `get_offers` | `POST /api/v1/offers` (#12) | `deliverBy` (ISO date), `items` (1–50) of `productCode` + optional `quantity` / `unit` (`L`, `KG` or a sales unit code), optional `language`; per item live `price`, `availability` (`availableAmount` null = unknown, not zero), `quantity` with `conversion` (+ `crossCheck`), `salesUnits` and `lineTotal`, `reasonCodes` (e.g. `CLOSING_TIME_PASSED`) and `provenance` (`fetchedAt`, `validUntil`, `cached`). Errors `PRODUCT_NOT_FOUND`, `CUSTOMER_NUMBER_MISSING`, `VALIO_AIMO_UNAVAILABLE`. For demos against the live mock, run the backend with `OFFERS_IGNORE_CLOSING_TIME=true` |
| `create_quote` | `POST /api/v1/quotes` (#14) | `deliverBy` (ISO date), `lines` (1–50) of `productCode` + `quantity` + optional `unit` (`L`, `KG` or a sales unit code) / `substitutesFor`, required `buyerRequest` and `rationale` (≤ 2,000 characters each, shown to approvers, never change the policy), optional `previousQuoteId`. Returns the quote: `quoteId`, `status`, `expiresAt`, per line the offer (as `get_offers`) plus `outcome` and `reasons`, `totals`, `deposits`, `policy` (`outcome` `AUTO_APPROVE` / `NEEDS_HUMAN` / `REJECT`, `reasons` with codes, severity, message and facts, `mandateVersion`). A `REJECT` is a normal result, not an error. Not idempotent: each call creates a quote. Errors `PRODUCT_NOT_FOUND`, `QUOTE_NOT_FOUND` (bad `previousQuoteId`), `CUSTOMER_NUMBER_MISSING`, `VALIO_AIMO_UNAVAILABLE` |
| `get_quote` | `GET /api/v1/quotes/{quoteId}` (#14) | `quoteId` (a UUID); the same quote shape, exactly as quoted. `status: "EXPIRED"` = past `expiresAt`, quote again. Error `QUOTE_NOT_FOUND` (unknown id or another organisation's) |
| `place_order` | `POST /api/v1/orders` (#15) | `quoteId` (a UUID, also the idempotency key: a retry never makes a second order). The backend re-checks live price, availability and the current mandate, so the order can differ from the quote: `changes` (`lineRef`, `field`, `quoted`, `now`) and `policy` (`outcome`, `reasons`, `mandateVersion`) say why. Returns the order: `orderId`, `quoteId`, `status` (`PLACED` / `PENDING_APPROVAL` / `REJECTED`; `CONFIRMED` / `APPROVED` are brief steps), `lines`, `totals`, `deposits`, `statusHistory` (`status`, `at`, `by`), `approverNote`, `decidedAt`, `checkAgainAfterSeconds` (while pending). `PENDING_APPROVAL` and `REJECTED` are normal results, not errors. Errors `QUOTE_EXPIRED` (quote again), `QUOTE_ALREADY_ORDERED` (the existing `orderId` is in the error text), `QUOTE_NOT_FOUND`, `CUSTOMER_NUMBER_MISSING`, `VALIO_AIMO_UNAVAILABLE`, `PERMISSION_DENIED` |
| `get_order_status` | `GET /api/v1/orders/{orderId}` (#15) | `orderId` (a UUID); the same order shape. Poll a `PENDING_APPROVAL` order no sooner than `checkAgainAfterSeconds`; `statusHistory` and `approverNote` explain a human decision. Error `ORDER_NOT_FOUND` (unknown id, or another agent's or organisation's order) |
| `list_orders` | `GET /api/v1/orders` (#15) | optional `status`, `limit` (1–100, default 20), `offset`; `total` and `items` (orders, most recent first) |

`find_substitutes` is added when its backend endpoint lands. There is no approve or reject tool: approving is user-only, and an agent can never approve its own orders.

## Run

```sh
cp .env.example .env     # once; points at the backend on :8000
uv run saint-elmo-mcp    # serves http://127.0.0.1:8001/mcp
```

## Connect an agent

Every request must carry an agent token (issued by a buyer admin, see ADR 0003), either as `X-Agent-Key: <token>` or as `Authorization: Bearer <token>`. The MCP server only checks that one is present and forwards it. The backend decides whether it's valid.

Claude Code:

```sh
claude mcp add --transport http saint-elmo http://localhost:8001/mcp \
  --header "X-Agent-Key: <agent token>"
```

Any other MCP client that can send custom headers on streamable HTTP works the same way.

## Errors

Policy outcomes (a rejection, needs approval, a shortfall) are normal tool results. Only failures come back as `isError` results, with text that starts with a code the agent can act on:

| Code | Meaning |
|---|---|
| `MISSING_AGENT_KEY` | No key on the request. The backend was not called. |
| `BACKEND_UNAVAILABLE` | Backend unreachable, or it failed without an error envelope. |
| `BACKEND_CONTRACT_MISMATCH` | Backend response didn't match the tool's output model (a Saint Elmo bug). |
| *backend codes* | Taken from the backend error envelope, e.g. `UNKNOWN_CODE`, `PRODUCT_NOT_FOUND`, `CUSTOMER_NUMBER_MISSING`, `VALIO_AIMO_UNAVAILABLE`, `MANDATE_NOT_FOUND`, `QUOTE_NOT_FOUND`, `QUOTE_EXPIRED`, `QUOTE_ALREADY_ORDERED`, `ORDER_NOT_FOUND`, `PERMISSION_DENIED`, `INVALID_CREDENTIALS`, `VALIDATION_ERROR`, with field details (or facts such as `orderId`) and the request id. |

## Tests

```sh
uv run pytest
```

The tests run the real server over streamable HTTP in-process, against a faked backend (`httpx.MockTransport`), so no backend or database is needed.
