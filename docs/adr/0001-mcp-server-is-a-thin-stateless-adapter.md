# The MCP server is a thin, stateless adapter with hand-written tools

`saint-elmo-mcp/` is its own uv project that never imports backend code and reaches the backend only over HTTP. It keeps no sessions (stateless streamable HTTP). On every tool call it reads the agent key from the request (`X-Agent-Key` or `Authorization: Bearer`) and forwards it as `Authorization: Bearer`. It holds no policy, validation or state, so an agent going through MCP can't skip anything a REST client would hit, and the backend stays the one place where rules are enforced.

Each tool is written by hand and maps to exactly one backend endpoint. Parameter names are the REST body's camelCase names. Typed output models cover only the fields an agent needs. The tool descriptions are written for an LLM, which is where this layer adds value.

## Considered options

- **Generating tools from the backend's OpenAPI** (e.g. `FastMCP.from_openapi`): rejected. The tool names and descriptions it produces are written for a human reading an API reference, not for an LLM, and description quality directly drives how precisely the agent matches the buyer request.
- **Composite tools** (e.g. one `find_options` doing search, offers and conversion in one call): rejected. They put orchestration in the MCP layer. If a combined call proves worth it, it becomes a backend endpoint that one tool wraps.
- **Mounting FastMCP inside FastAPI**: kept only as a fallback. A separate process can fail and be exposed on its own, and it shows that MCP is just one way into the same API.

## Consequences

- Policy outcomes (`REJECT`, `NEEDS_HUMAN`, shortfalls) are normal tool results. Only transport, auth and validation failures become MCP `isError` results, carrying the backend error envelope's `code`, `message` and `details`.
- Output models duplicate a subset of the backend's response shapes. That's intended: when the contract drifts, MCP tests fail.
- Input schemas may mirror the backend's field types and bounds (e.g. `limit` 1–100, `minDeliveryReliability` 0–1) so the agent sees them up front. They never add a rule the backend doesn't enforce, and the backend stays authoritative. A mirrored bound must change together with the backend's.
- A tool may take a presentation-only parameter that trims a read-only response to save the agent's context (e.g. `get_vocabulary`'s `vocabularies`). It never filters which records the agent may see, and never changes what the backend is asked. If REST clients would want the same trim, it becomes a backend parameter.
- The MCP server requires an agent key from day one, even before the backend checks keys, so client configuration never has to change.
