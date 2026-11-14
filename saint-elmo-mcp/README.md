# Saint Elmo MCP server

The way into Saint Elmo for purchasing agents that speak MCP. It's a thin, stateless adapter. Each tool calls one Saint Elmo backend endpoint over HTTP, passing along the caller's agent key, and the backend does all validation, policy, state and audit. Why it's built this way: [ADR 0001](../docs/adr/0001-mcp-server-is-a-thin-stateless-adapter.md).

Built on the official MCP Python SDK v2 (`MCPServer`, which was called `FastMCP` in v1), serving stateless streamable HTTP.

## Tools

| Tool | Backend endpoint | Status |
|---|---|---|
| `search_products` | `POST /api/v1/products/search` (#2, #3, #4) | query, language, paging; filters `categoryCodes`, `vendors`, `requiredClaims`, `requiredDiets`, `requiredLabels`, `countriesOfOrigin`, `minDeliveryReliability`; allergen exclusion `excludedAllergens` + `allergenStrictness` (`contains` / `may_contain` / `declared_free`); per-hit `allergens` status (`UNKNOWN` = no data, not safe) |

The remaining tools (`get_product`, `get_vocabulary`, `get_my_mandate`, `get_offers`, `find_substitutes`, `create_quote`, `place_order`, `get_order_status`) are added as their backend endpoints land. See issues #10–#16.

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
| *backend codes* | Taken from the backend error envelope, e.g. `UNKNOWN_CODE`, `INVALID_CREDENTIALS`, `VALIDATION_ERROR`, with field details and the request id. |

## Tests

```sh
uv run pytest
```

The tests run the real server over streamable HTTP in-process, against a faked backend (`httpx.MockTransport`), so no backend or database is needed.
