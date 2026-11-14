# MCP server tracer bullet: `search_products`

## What to build

The tracer bullet for the MCP layer: a new `saint-elmo-mcp/` sub-project with exactly one tool, `search_products`, wrapping `POST /api/v1/products/search` from #2. It establishes the whole pipeline (key forwarding, error mapping, typed outputs, server instructions, tests) before the backend ships any endpoint. Shape and reasons: ADR 0001.

**Project**

- Its own uv project (`pyproject.toml`, `uv.lock`), Python 3.13, depending on `mcp` (official SDK, `FastMCP`), `httpx`, `pydantic` and `pydantic-settings`. It **does not import `saint_elmo_backend`.**
- Settings from env: `BACKEND_BASE_URL` (default `http://localhost:8000`), `MCP_HOST`/`MCP_PORT` (default `:8001`). A committed `.env.example`.
- Runs with `uv run saint-elmo-mcp` as stateless streamable HTTP at `/mcp`.

**Credential forwarding**

- Every tool call reads the agent key from the incoming HTTP request: `X-Agent-Key`, falling back to `Authorization: Bearer <key>`.
- It is forwarded to the backend as `Authorization: Bearer <key>`. No caching and no validation beyond "present".
- A missing key gives an `isError` result with code `MISSING_AGENT_KEY` and a message saying which header to set. The backend is not called.

**Backend client**

- One async `httpx` client module. It maps the backend error envelope (`{"error": {"code", "message", "requestId", "details"}}`) to an `isError` tool result whose text the agent can act on, e.g. `UNKNOWN_CODE: Unknown codes: requiredLabels=[ORGANIC] (request 1f3…)`.
- If the backend can't be reached, or answers with a non-envelope 5xx, the result is `isError` with code `BACKEND_UNAVAILABLE`.

**`search_products` tool**

- Parameters are #2's request fields with their REST names: `query`, `language` (default `en`), `limit` (**default 10** here, max 100), `offset`. #3/#4 filters are added in follow-up issues.
- The output is a typed Pydantic model mirroring the fields of #2's response that an agent needs (`total`, `items[]`, `provenance`), so it shows up as `outputSchema` and `structuredContent`.
- Annotations: `readOnlyHint: true`, `openWorldHint: false`.
- The description, written for an LLM, says:
  - this searches the static catalog only, with no live prices or stock (that comes from `get_offers`)
  - null `deliveryReliability` means no history, not unreliable
  - CO₂ is a product-group average

**Server `instructions`**, a short workflow guide covering:

- the intended flow: `get_my_mandate` → `search_products` → `get_offers` → `create_quote` → `place_order` → poll `get_order_status`
- resolve relative dates to ISO dates yourself
- state quantities in buyer units
- unknown ≠ free-from
- policy rejections are answers, not errors

Only the tools that exist are named. The rest of the text says it describes the full flow.

**README** covering how to run the server and how to connect Claude Code, e.g. `claude mcp add --transport http saint-elmo http://localhost:8001/mcp --header "X-Agent-Key: <key>"`.

## Acceptance criteria

- [ ] An in-memory MCP client session lists exactly one tool, `search_products`, with an input schema using #2's field names and an output schema.
- [ ] A call forwards `X-Agent-Key: k1` as `Authorization: Bearer k1`, and `Authorization: Bearer k1` is forwarded unchanged (checked against an `httpx.MockTransport` fake of #2).
- [ ] A call without a key returns `isError` `MISSING_AGENT_KEY` and makes no backend request.
- [ ] A backend 422 `UNKNOWN_CODE` envelope comes back as `isError` text containing the code, message, details and request id.
- [ ] An unreachable backend returns `isError` `BACKEND_UNAVAILABLE`.
- [ ] `limit` defaults to 10 and values above 100 are rejected by the tool schema.
- [ ] A successful call returns `structuredContent` that validates against the output schema.
- [ ] The server starts with `uv run saint-elmo-mcp` and Claude Code can connect to it using the README snippet.
- [ ] No module in `saint-elmo-mcp/` imports `saint_elmo_backend`.
