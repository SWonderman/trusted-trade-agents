# Design — MVP architecture

Context and data analysis: [CHALLENGE_OUTLINE.md](CHALLENGE_OUTLINE.md). The trust model this design implements is in section 6 of that outline.

## 1. Overview

```
┌────────────────────────┐         ┌──────────────┐        ┌──────────────────────────────┐        ┌─────────────────────┐
│ Buyer's agents         │  MCP    │ MCP server   │  REST  │ Backend                      │  REST  │ Valio Aimo mock API │
│ (untrusted clients,    │ ──────▶ │ (thin        │ ─────▶ │ validation, policy,          │ ─────▶ │ /api/price          │
│  one key per agent)    │         │  adapter)    │        │ orchestration, state, audit  │        │ /api/availability   │
└────────────────────────┘         └──────────────┘        └──────────────────────────────┘        └─────────────────────┘
                                                                  ▲              ▲
                                                             REST │              │ static data (catalogue,
                                                                  │              │ reliability, CO₂)
                                                           ┌──────┴───────┐
                                                           │ Frontend     │
                                                           │ mandates,    │
                                                           │ approvals,   │
                                                           │ audit log    │
                                                           └──────────────┘
                                                             Human users
```

Four parts:

1. **Buyer's agents.** A client organisation runs several agents, each sent to do a specific task. They are untrusted.
2. **MCP server.** The gateway agents use to talk to our system.
3. **Backend.** Validates and orchestrates everything, and is the only part that talks to the Valio Aimo API.
4. **Frontend.** Where humans set agent boundaries (mandates) and handle what agents couldn't resolve themselves (approvals and exceptions).

## 2. Guiding principles

- **Keep the MCP server thin, with all logic in the backend.** The MCP server only maps tool calls to backend endpoints and forwards the agent's credential. It holds no policy, validation or state.
- **One place enforces the rules.** The MCP server and the frontend call the same backend API, so every rule is checked in exactly one place.
- **Expose the same API two ways.** Publish the backend's agent-facing API as OpenAPI as well as through MCP. MCP is one way in and REST is another, and the brief leaves the production form open. This costs almost nothing and helps the "openness" score.
- **Use deterministic code for every decision.** No language model runs on the backend. Every decision has a reason code and the same input gives the same result, so the audit trail can be reproduced.
- **Don't build the buyer's agent as a product.** Any MCP client (Claude Desktop, Claude Code) connected with an Agent token is enough. That also demonstrates the system is open.

## 3. Components

### 3.1 Buyer's agents (clients)

- **Each agent gets its own identity and Agent tokens bound to one mandate.** A buyer admin issues tokens in the frontend, with Scopes and an expiry; each can be revoked immediately. The token references the mandate but never carries its limits (see [ADR 0003](docs/adr/0003-agent-tokens-reference-server-mandate.md)). Example agents:
  - `dairy-restock`: dairy categories only, €2,000 per-order limit, substitutes must keep `FREE_FROM_LACTOSE`.
  - `event-planner`: may order from any category, but every substitution needs approval.
- **Demo client:** Claude Desktop or Claude Code connected to the MCP server.
- **Optional scripted agent** (using the Claude API), for repeatable demo runs or several agents running at once.
- **The agent cannot change or widen its own mandate.** It can only read it, through `get_my_mandate`.

### 3.2 MCP server (gateway)

- **The credential:** an Agent token (EdDSA-signed JWT, see [ADR 0003](docs/adr/0003-agent-tokens-reference-server-mandate.md)), pasted into the MCP client config and sent as `X-Agent-Key` or `Authorization: Bearer <token>`; the MCP server forwards it untouched (ADR 0001). Next step: the MCP specification's OAuth flow, issuing the same JWT.
- **Tools.** Each one is a thin wrapper around a backend endpoint:

| Tool | Purpose |
|---|---|
| `get_my_mandate` | Read own limits, so the agent can pre-check and avoid proposals that will be rejected |
| `search_products` | Search the catalogue by text, category, claims (e.g. lactose-free), allergens and labels |
| `get_offers` | Live price and availability for a shortlist (up to N products), plus delivery reliability, CO₂ and where each value came from |
| `find_substitutes` | Ranked good/better/best alternatives for a product, under the stated rules |
| `create_quote` | Put a basket together: convert quantities, check minimum order steps, price it, run the policy check. Returns a quote with an expiry |
| `place_order` | Commit a quote. The live data is re-checked, then the result is `confirmed` or `pending_approval` |
| `get_order_status` | Check on orders that are pending, approved, rejected or placed |

- **Approval is asynchronous.** `place_order` never waits for a human. It returns `pending_approval` with an id, and the agent checks back with `get_order_status`.

### 3.3 Backend

| Module | Responsibility |
|---|---|
| **Catalogue index** | Loads the 17.5k products and both CSVs. Searchable by text (fi/en/sv), category, claims, allergens, labels, vendor and origin. Stored in Postgres, searched with full-text search plus `pg_trgm` for fuzzy matching. Global: shared by all buyer organisations, with no `org_id`. |
| **Valio Aimo API client** | Calls `/api/price` and `/api/availability` for shortlists only, batched (≤1,000 per call), cached within each price's validity window, and respecting rate limits. |
| **Quantity normaliser** | Converts the requested quantity (litres or kg) into sales units, rounds to `allowedLotSize`, and shows the conversion (litres per sales unit from `catalogPrice / comparisonPrice`, cross-checked against the product name and `unitConversions`). |
| **Offer ranking and substitution** | Ranks candidates by price, available date versus deadline, delivery reliability, CO₂ and labels. Substitutes must keep the required claims and allergen exclusions, starting from the curated substitution rules and widening to attribute-based search within the same category. |
| **Quote and order service** | The state machine (see 3.5). Holds orders itself, because the mock API has no order endpoint. Re-checks price, availability and `closingTime` when an order is placed. |
| **Policy engine** | Checks a quote or order against the agent's mandate. Returns `auto_approve`, `needs_human` or `reject` with reason codes. |
| **Audit log** | Append-only record of every tool call, decision, approval and state change: who did what, when, why, and with what data. Readable by the buyer and by Aimo. Optionally hash-chained. |
| **Scenario controls** | Demo-only availability overrides (e.g. "product X is out of stock from Wednesday"), so exception scenarios can be reproduced. |

### 3.4 Frontend

- **Buyer admin (MVP):**
  - Agents and their mandates: create an agent, set limits, issue Agent tokens (Scopes, label, expiry; shown once) and revoke them.
  - Approval inbox: each pending order shows the agent's explanation alongside the policy's reasons (e.g. "over the €2,000 limit", "substitute isn't marked lactose-free"). Approve or reject.
  - Audit log viewer, per agent and per order.
- **Aimo-side view (stretch):** a read-only view of all agent activity across customers, to show the log is readable by both buyer and Valio Aimo.

**Stack and authentication:**

- **SvelteKit (Svelte 5) acts as the backend-for-frontend.** The browser only ever talks to SvelteKit. SvelteKit's server-side code (`load` functions, form actions, `hooks.server.ts`) calls FastAPI. There is no CORS to configure, and no JavaScript in the browser can read the token.
- **Login:**
  1. A SvelteKit form action posts the credentials to FastAPI's `POST /auth/login`.
  2. FastAPI returns a signed JWT with these claims: `sub` (user id), `org_id`, `role`, `exp`.
  3. SvelteKit stores the JWT in a cookie with `httpOnly`, `Secure`, `SameSite=Lax` and `Path=/`.
- **On every request:**
  1. `hooks.server.ts` reads the cookie, checks it hasn't expired, and puts the user in `event.locals`.
  2. Server-side calls to FastAPI forward the JWT as `Authorization: Bearer <jwt>`.
  3. FastAPI verifies the signature and resolves the user, whose `org_id` scopes the request (see 3.7).
- **Signing:** HS256 with one shared secret (`JWT_SECRET` env var), known only to FastAPI. SvelteKit doesn't verify the signature; it only reads `exp` to redirect to login early, and FastAPI verifies every request. Next step: RS256 or EdDSA, for key rotation and so other services can verify tokens.
- **Approval inbox updates:** the inbox page polls (re-runs its `load` every 5–10 s with `invalidate`). Agents poll `get_order_status` the same way. Next step: server-sent events.
- **Token lifetime:** short-lived access tokens (e.g. 60 minutes). No refresh token in the MVP; the user logs in again. Logout clears the cookie.
- **CSRF:** `SameSite=Lax` plus SvelteKit's built-in origin check on form actions. Anything that changes state (approve, reject, edit a mandate) goes through form actions.
- **Two separate authentication schemes in FastAPI:**
  - human users: JWT bearer tokens, issued through SvelteKit
  - agents: Agent tokens (EdDSA-signed JWTs with a separate key, public key at `/.well-known/jwks.json`), coming in through the MCP server or directly. Each request checks the token's `jti` against its credential row, so revocation is immediate, and each route declares the Scope it requires
  Both resolve to the same principal (`org_id` plus `user_id` or `agent_id`), so services and the audit log treat them the same way. Each route declares which scheme it accepts. Approving orders is for users only, so no Agent token can ever approve; there is no approve Scope.

### 3.5 Quote and order lifecycle

```
create_quote ─▶ QUOTED ──(expiry / closingTime passed)──▶ EXPIRED
                  │
             place_order (live re-check + policy check)
                  │
     ┌────────────┼──────────────────────┐
     ▼            ▼                      ▼
 CONFIRMED   PENDING_APPROVAL ◀─┐     REJECTED (policy hard-fail)
 (auto)           │             │
     │      human approves / rejects (approval re-checks live data)
     │       │            │     │
     │       ▼            ▼     └─ new NEEDS_HUMAN reason or higher total:
     │    APPROVED     REJECTED      stays pending, to be decided again
     │       │
     ▼       ▼
   PLACED (recorded in our order book; the mock API has no order endpoint)
```

- **A failed re-check creates no order.** If the Valio Aimo API is unavailable when an order is placed, the agent gets an error and the quote stays orderable. One quote gives at most one order, so rejecting it would use the quote up over an outage.
- **An approval never commits more than the approver saw.** The approval re-check rejects the order if a hard-fail now applies (e.g. the closing time has passed). A needs-human reason the order wasn't pending with, or a total above the one it was pending with, keeps it pending with the new reasons and total shown, to be decided again.

### 3.6 Mandate model (first draft)

The fields of a mandate:

- **Spend:** maximum per order; maximum per period (week or month); maximum per category.
- **Assortment:** categories allowed or blocked; vendors allowed or blocked; origins allowed.
- **Requirements:** required claims (e.g. `FREE_FROM_LACTOSE`); excluded allergens (`CONTAINS`, and optionally `MAY_CONTAIN`); required labels.
- **Substitutions:** never allowed / allowed if all requirements still hold / always need approval; maximum price increase in %.
- **Delivery:** whether a later date than requested is acceptable without approval; minimum delivery reliability.
- **Escalation:** anything outside these bounds → `needs_human`. Hard violations (a blocked allergen, a sales block) → `reject`.

### 3.7 Buyer organisations

The demo has no tenant isolation in the database ([ADR 0004](docs/adr/0004-buyer-organisation-is-a-plain-foreign-key.md)). A buyer organisation is a plain foreign key, and services filter by it.

**Data model.** `organization` holds the buyer organisation's name and its Valio Aimo customer number, which is passed to the mock API. These tables carry `org_id`, a foreign key to it:

- `user`, `agent`, `agent_credential`, `mandate`
- `quote`, `quote_line`, `order`, `order_line`, `approval`, `audit_event`

Global tables, which have no `org_id`:

- the catalogue and its derived search tables
- delivery reliability and carbon footprint
- the cache of Valio Aimo API responses

Prices and availability are customer-specific in reality but not in the mock. Key the cache by customer number anyway, so moving to real customer-specific data later is easy.

**How a request gets its buyer organisation:**

1. An agent's Agent token (MCP or REST) or a user's session (frontend) is resolved to a principal, an `org_id` plus an `agent_id` or `user_id`, by a FastAPI dependency. The client never sends a buyer organisation or customer id itself.
2. Services that read or change buyer-owned data take the `org_id` from the principal as a required argument and filter by it in the query. It's an argument, not ambient request state, so a missing filter shows in the code.
3. A user belongs to exactly one buyer organisation. There are no memberships and no switching between organisations.

**Database:** one role owns the tables, runs Alembic and serves the application.

**Tests:** HTTP-level tests check that a user of buyer organisation B can't see or change A's agents, Agent tokens, quotes, orders or approvals.

**Production step:** Postgres row-level security on the existing `org_id` columns: `ENABLE` and `FORCE ROW LEVEL SECURITY` with a policy on `current_setting('app.org_id')`, a per-transaction `SET LOCAL app.org_id`, and a non-owner runtime role without `BYPASSRLS`. It needs no change to the data model.

**MVP roles and seed data:**

- Roles: `buyer_admin` (manages agents and mandates, approves orders) and optionally a separate `approver`. `aimo_staff` only if the Aimo view gets built.
- Two seeded organisations:
  - a hotel chain, for the milk scenario and its spend limits
  - a hospital kitchen, with strict allergen rules and every substitute needing approval
- Out of scope: self-signup, invitations, SSO, users in several buyer organisations, row-level security, billing.

## 4. Tech stack

| Concern | Choice | Notes |
|---|---|---|
| Language and packaging | Python 3.12+, **uv** | `uv` workspace if the backend and MCP server become separate packages; `uv.lock` committed |
| Backend API | **FastAPI** + Pydantic v2 | OpenAPI generated automatically; reuse the existing HTTP code |
| Database | **PostgreSQL** (16+) | Also runs catalogue search (full-text search + `pg_trgm`); row-level security is the production step for isolating buyer organisations |
| ORM / migrations | **SQLAlchemy 2.x** (async, `asyncpg`) + **Alembic** | |
| Buyer organisations | Plain `org_id` foreign key, filtered in services | See 3.7 and [ADR 0004](docs/adr/0004-buyer-organisation-is-a-plain-foreign-key.md) |
| Valio Aimo API client | `httpx` (async) | Batching, caching within each price's validity window, retry and backoff on rate limits |
| MCP server | Official MCP Python SDK (`FastMCP`) | Separate process, streamable HTTP transport; calls the backend's REST API with the agent's key (see 4.1) |
| Orchestration | **Docker Compose** | Whole system with one `docker compose up` (see 4.1) |
| Frontend | **SvelteKit** (Svelte 5, TypeScript) | Backend-for-frontend: server-side `load` functions and actions call FastAPI; TS types can be generated from FastAPI's OpenAPI |
| Auth (users) | **JWT in an `httpOnly` cookie** | Issued by FastAPI, set by SvelteKit, forwarded server-to-server as a bearer token; see 3.4 |
| Auth (agents) | Agent token (EdDSA JWT + JWKS) | Issued per agent in the frontend; references the mandate, never embeds it; `jti` stored for revocation; sent by the MCP client to the MCP server, which forwards it to FastAPI. See [ADR 0003](docs/adr/0003-agent-tokens-reference-server-mandate.md) |

### 4.1 Deployment (Docker Compose)

**The MCP server runs as its own process.** It can reach the backend only over HTTP, using the agent's key. That keeps it a thin adapter: it can't skip authentication, mandate checks or the audit log. It also shows that MCP is just one way into the same API that REST clients use, and it can be exposed and fail independently of the backend. Mounting FastMCP inside FastAPI remains a fallback, not the plan.

| Service | Runs | Depends on | Exposed |
|---|---|---|---|
| `db` | Postgres 16, with a healthcheck | — | no (optionally `127.0.0.1:5432`, for debugging) |
| `migrate` | One-off job: `alembic upgrade head`, then the seed (catalogue, CSVs, demo organisations and users) | `db` healthy | — |
| `backend` | FastAPI on `uvicorn` | `migrate` completed successfully | `:8000` (REST and OpenAPI docs; agents may also use it directly) |
| `mcp` | FastMCP over streamable HTTP; calls only `http://backend:8000` | `backend` | `:8001/mcp` |
| `frontend` | SvelteKit (`adapter-node`); server-side code calls `http://backend:8000` | `backend` | `:3000` |

- **One Python image** (uv workspace, `uv sync --frozen`) serves `migrate`, `backend` and `mcp`, with a different command per service. The frontend has its own Node image.
- **Configuration** goes in `.env`, which is not committed (a committed `.env.example` lists the variables): `VALIO_API_BASE_URL`, `VALIO_API_KEY`, `JWT_SECRET`, `AGENT_TOKEN_SIGNING_KEY` (Ed25519 private key), `DB_PASSWORD`.
  - The `mcp` and `frontend` services only need the backend's URL. They never see the Valio Aimo key or the database credentials.
- **Development:** run only `db` (and `migrate`) in Compose, and run `backend`, `mcp` and `frontend` on the host with hot reload. The demo or judging setup is the full `docker compose up`.
- **Connecting a demo agent:**
  - Claude Code can add a remote HTTP MCP server at `http://localhost:8001/mcp`, with the Agent token in the `X-Agent-Key` header or as `Authorization: Bearer <token>` (ADR 0001).

## 5. Build order (scope control)

1. **Backend core:** catalogue index, API client, quantity normaliser, quotes and orders.
2. **The milk request end to end** ("1,000 L lactose-free milk by Monday") through Claude Desktop, then MCP, then the backend.
3. **Policy engine and audit log**, then asynchronous approval.
4. **Frontend:** mandates, approval inbox, audit log.
5. **Exception scenarios**, using the scenario controls: partial availability, stock-out, then a ranked substitute, then approval.
6. **Stretch:** the Aimo-side view, signed offers, push notifications for at-risk order lines.

## 6. Open decisions

- What period-based spend limits mean when orders are only mocked.
- For production, once row-level security is added (ADR 0004): how Aimo's cross-customer read access to `audit_event` fits with it, either as a separate policy or as a separate read-only view.
