# Issue drafts (for review, then filing)

These are drafts of the GitHub issues for the MCP layer and the order side of the backend, which issues #2–#7 don't cover. Review them in this PR. Once they're agreed, each is filed as a GitHub issue labelled `needs-triage` and this folder is deleted.

Background: [ADR 0001](../adr/0001-mcp-server-is-a-thin-stateless-adapter.md), [ADR 0002](../adr/0002-agent-backend-division-of-decisions.md), [GLOSSARY.md](../../GLOSSARY.md), [design.md](../../design.md).

| Draft | Title | Backs MCP tool | Blocked by |
|---|---|---|---|
| [01](01-mcp-tracer-bullet.md) | MCP server tracer bullet: `search_products` | `search_products` | — (fakes #2) |
| [02](02-agent-mandate.md) | Agent mandate model and read endpoint | `get_my_mandate` | #7 |
| [03](03-live-offers.md) | Live offers with quantity conversion | `get_offers` | #2 |
| [04](04-policy-engine.md) | Policy engine and reason codes | — (used by 05–07) | 02 |
| [05](05-quotes.md) | Quotes | `create_quote` | 03, 04 |
| [06](06-orders-and-approval.md) | Orders, approval and order status | `place_order`, `get_order_status` | 05 |
| [07](07-substitutes.md) | Ranked substitutes | `find_substitutes` | #3, #4, #5, 03, 04 |

Not drafted here, but needed:

- **Audit trail.** Drafts 02 and 04–07 say what each step must record, but there's no issue for the audit trail itself yet.
- **Frontend work:** mandate editing, the approval inbox and the audit viewer.
- **Root `compose.yml`** for the full stack (design §4.1).
- **MCP follow-ups.** Each backend issue above gets a small matching MCP issue ("wrap endpoint X as tool Y") once its contract is merged. MCP issues for `get_product` (#5) and `get_vocabulary` (#6) can be filed now.

## Conventions used in every draft

- JSON bodies are camelCase, as in #2. Enum values in responses are UPPER_SNAKE (`NEEDS_HUMAN`, `PENDING_APPROVAL`, `PARTIAL_AVAILABILITY`), as with #4's allergen statuses.
- Failures use the existing error envelope (`{"error": {"code", "message", "requestId", "details"}}`) with new `ErrorCode` values. **Policy outcomes and shortfalls are not errors**: they come back as 200 responses with reason codes.
- Agent-facing routes accept the agent scheme from #7. Routes that change a human decision (approve/reject) accept the user scheme only.
- `deliverBy` is always an ISO date resolved by the agent and repeated back in the response (ADR 0002).
