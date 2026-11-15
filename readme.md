# Saint Elmo

A gateway that lets a buyer organisation's autonomous purchasing agents find, compare and order Valio Aimo products **within limits a person sets**, with every decision explainable afterwards.

Built for the Valio Aimo challenge at Junction 2026. All data and the Valio Aimo API it calls are synthetic mocks.

> Saint Erasmus, called Saint Elmo, is the patron of sailors. A blue fire on the mast in a storm was taken as his sign that the ship was being watched over. Saint Elmo keeps that watch over agents that buy on your behalf.

## The problem

Valio Aimo serves more than 20,000 professional kitchens. Today a buyer logs into the webshop and clicks through a catalog. Soon, more and more of those orders will be placed by AI agents working for the buyer: "I need 1,000 litres of lactose-free milk by Monday" goes in, and an order comes out.

That raises three questions the webshop was never built to answer:

- **What may an agent see and do?** An agent is software, and software can be wrong, prompt-injected or simply over-eager. Valio Aimo can't hand it the keys to the backend.
- **What may it decide alone, and what must wait for a person?** A hotel chain is happy to let an agent restock milk up to a few hundred euros. It is not happy to discover a €20,000 order, or a substitute with an allergen the hospital kitchen excludes.
- **Who can explain what happened afterwards?** When an order goes wrong, both the buyer and Valio Aimo need a record of what the agent asked for, what it was shown and who decided what.

Saint Elmo is the interface and operating model that answers them, built on open standards rather than one platform's black box.

## What it does

A person at the buyer organisation (the **buyer admin**) creates an agent in the console and writes its **mandate**: how much it may spend per order and per week or month, which categories, vendors and origins it may buy, which claims it needs (e.g. `FREE_FROM_LACTOSE`), which allergens it must avoid and how strictly, whether it may substitute, and up to what amount it may decide alone. They issue the agent a signed, expiring, scoped **Agent token**.

The agent connects over MCP (Claude Code, Claude Desktop, or any MCP client) or plain REST, and works through one flow:

| Step | Agent calls | Saint Elmo does |
| --- | --- | --- |
| 1. Read the rules | `get_my_mandate` | Shows the agent its whole mandate and what's left of its period spend. The agent can read it, never change it. |
| 2. Search | `search_products`, `get_vocabulary`, `get_product` | Searches 17,500 products by what they declare: claims, diets, labels, allergens, categories. A product with no allergen data is `UNKNOWN`, never "free from". |
| 3. Price and stock | `get_offers` | Asks the live Valio Aimo API for a shortlist only, converts the buyer's litres or kilos into the sales units Valio Aimo sells (and shows the conversion), and labels every figure with where it came from and how long it holds. |
| 4. Handle shortfalls | `find_substitutes` | On partial stock, late delivery or a sales block, ranks substitutes as `BEST` / `BETTER` / `GOOD`, with their trade-offs (price, date, reliability, CO₂, claims kept or lost) and a preview of what the policy would say. |
| 5. Quote | `create_quote` | Judges the basket against the mandate and returns one **policy outcome**, `AUTO_APPROVE`, `NEEDS_HUMAN` or `REJECT`, with reason codes such as `OVER_AUTO_APPROVE_LIMIT` or `MAY_CONTAIN_EXCLUDED_ALLERGEN`. The agent records the buyer's words and its own rationale. |
| 6. Order | `place_order`, `get_order_status` | Re-checks live price, stock, closing time and the current mandate, then places the order, rejects it with reasons, or sends it to a person. |
| 7. Explain | `get_order_trail`, `get_audit_log` | Reads back the order's audit trail in plain language. |

An order that needs a person lands in the console's **Approvals**, next to the policy's reason codes, the agent's rationale, the unit conversions and the substitutes it considered. The **approver** approves (which re-checks live data once more) or rejects with a note. There is no approve tool: an agent can never approve its own orders.

## Principles

- **A person sets the mandate; the agent can only read it.** The Agent token names the mandate but never carries its limits, so the policy always applies the mandate as Saint Elmo holds it now, and revoking a token takes effect on the next request ([ADR 0003](docs/adr/0003-agent-tokens-reference-server-mandate.md)).
- **Code judges, not a model.** No language model runs in the backend. The policy is deterministic: the same quote and mandate always give the same outcome and reason codes, so any decision can be replayed. The agent interprets and chooses; the backend converts, checks and enforces ([ADR 0002](docs/adr/0002-agent-backend-division-of-decisions.md)).
- **Rules live in one place.** The MCP server, REST clients and the console all go through the same backend API, so an agent can't skip a check by picking a different door ([ADR 0001](docs/adr/0001-mcp-server-is-a-thin-stateless-adapter.md)).
- **Everything is written down.** Every quote, substitute request, order, approval and change to an agent's authority goes into an append-only audit trail, readable by the buyer organisation and shareable with Valio Aimo.
- **Unknown is not safe.** Stock shipped by a supplier is marked unknown, not counted as plenty. Missing allergen data is shown as missing. Carbon figures are labelled as product-group averages.
- **Ask Valio Aimo only for what's needed.** Search runs on the static catalog; only a shortlist goes to the live price and availability API, batched and cached within each price's validity window.

## How it's structured

```
┌───────────────────┐  MCP   ┌──────────────┐  REST  ┌──────────────────────────────┐  REST  ┌─────────────────────┐
│ Buyer's agents    │ ─────▶ │ MCP server   │ ─────▶ │ Backend                      │ ─────▶ │ Valio Aimo mock API │
│ (untrusted, one   │        │ thin adapter │        │ catalog, policy, quotes,     │        │ price, availability │
│  token per agent) │ ─────────── REST ────────────▶ │ orders, audit, Postgres      │        └─────────────────────┘
└───────────────────┘                                └──────────────────────────────┘
                                                                   ▲ REST
                                                     ┌─────────────┴────────────┐
                                                     │ Console (frontend)       │
                                                     │ agents, mandates, tokens,│
                                                     │ approvals, audit trail   │
                                                     └──────────────────────────┘
                                                            buyer admins, approvers
```

| Folder | What it is |
| --- | --- |
| [`saint-elmo-backend/`](saint-elmo-backend) | FastAPI, Pydantic v2, SQLAlchemy 2 (async) and Alembic on PostgreSQL. The only part that holds state, enforces the mandate or talks to Valio Aimo. Modules per domain: `catalog`, `offers`, `substitutes`, `quotes`, `orders`, `policy`, `mandates`, `agents`, `accounts`, `audit`, `valio_aimo`. Serves its own OpenAPI 3.1 schema at `/docs`. |
| [`saint-elmo-mcp/`](saint-elmo-mcp) | The MCP server, on the official MCP Python SDK over stateless streamable HTTP. Each tool calls one backend endpoint, forwarding the Agent token untouched; it imports no backend code and holds no rules. Its README lists every tool. |
| [`saint-elmo-frontend/`](saint-elmo-frontend) | The console, in SvelteKit (Svelte 5), Tailwind CSS 4 and shadcn-svelte, run as a backend-for-frontend: the browser only talks to SvelteKit. A marketing page, then Approvals, Agents and mandates (issue and revoke Agent tokens), a read-only Catalog for writing mandates, the Audit trail, and a Valio Aimo oversight view (still demo data). |
| [`demo/buyer-agent/`](demo/buyer-agent) | A ready-made purchasing agent: start `claude` in this folder and it connects to Saint Elmo over MCP with a buyer's persona and nothing of this repo in its context. Its README has sample prompts. |
| [`data/`](data) | The challenge data set: 17,546 products (with GS1 Synkka data), delivery reliability and category CO₂ averages. Not committed. |
| [`docs/adr/`](docs/adr) | Architecture decision records. |
| [`GLOSSARY.md`](GLOSSARY.md) | The domain language: mandate, quote, offer, shortfall, policy outcome, reason code, audit trail and the rest. |
| [`design.md`](design.md) | The MVP architecture: components, auth, quote and order lifecycle, tech stack, deployment. |
| [`CHALLENGE_OUTLINE.md`](CHALLENGE_OUTLINE.md) | The challenge, the judging criteria and what the data and mock API do and don't provide. |
| [`openapi.json`](openapi.json) | Valio Aimo's mock API, as given by the challenge. |
| [`compose.yml`](compose.yml), [`justfile`](justfile) | The whole stack in Docker, and shortcuts for common tasks. |

### Demo organisations

The seed creates two buyer organisations, each with a buyer admin and an agent. Every password is `saint-elmo-demo`.

| Buyer organisation | Buyer admin | Agent and mandate |
| --- | --- | --- |
| Aurora Hotels | `buyer.admin@aurora-hotels.example` | `dairy-restock`: lactose-free only, decides alone up to €1,500, never above €2,000 per order, €5,000 a week; substitutes may cost at most 10% more. |
| Kuusikko Hospital Kitchen | `buyer.admin@kuusikko-hospital.example` | `ward-kitchen`: nothing containing milk or gluten, declared free only; decides alone up to €1,000, never above €3,000 per order, €12,000 a month; every substitute needs approval. |

### Open standards

- **MCP** for agents, and the same API as **REST**, described in **OpenAPI 3.1** with **JSON Schema** responses.
- **GS1** code lists for allergens, claims, diets, labels and packaging, as in Valio Aimo's own product data.
- Agent tokens are **EdDSA-signed JWTs** with a published **JWKS**; the next step is the MCP specification's OAuth flow issuing the same token.

## Run everything with Docker

1. Create `saint-elmo-backend/.env` from `saint-elmo-backend/.env.example` and fill in the generated keys (`JWT_SECRET`, `AGENT_TOKEN_SIGNING_KEY`, `CREDENTIAL_KEYS`) and the Valio Aimo API settings (`VALIO_AIMO_API_URL`, `VALIO_AIMO_API_KEY`) from the challenge portal.
2. Put the challenge data set in `data/` (the product JSON and the two CSVs).
3. From the repo root:

   ```sh
   docker compose up --build      # or: just up
   ```

   The first start migrates and seeds its own database, which takes a few minutes. It's a separate database from the one `saint-elmo-backend/compose.yml` runs for development and tests.

| What | Where |
| --- | --- |
| Console | http://localhost:3000, sign in as `buyer.admin@aurora-hotels.example` or `buyer.admin@kuusikko-hospital.example`, password `saint-elmo-demo` |
| MCP server | http://localhost:8001/mcp |
| Backend API | http://localhost:8000/docs |

Ports are loopback only. Move them with `BACKEND_PORT`, `MCP_PORT` and `FRONTEND_PORT` if something else uses them (the console's connect snippet follows `MCP_PORT`). `OFFERS_IGNORE_CLOSING_TIME` defaults to `true` in this stack, because the live mock's closing times have already passed; set it to `false` to see those rejections.

### Connect an agent

In the console, open Agents → an agent → Agent tokens → Issue. Copy the `claude mcp add …` command it shows and run it once; then start `claude` anywhere and ask it to buy something. Orders that need a person show up in the console's Approvals.

Without the console, `just compose-token dairy-restock buyer.admin@aurora-hotels.example` issues a token from the running stack.

For a cleaner demo, start `claude` in [`demo/buyer-agent/`](demo/buyer-agent) instead, which gives it the purchasing-agent persona. Try:

- "We need 1,000 litres of lactose-free milk by Monday." (as `dairy-restock`)
- "Order 40 kilos of oat flakes for porridge on the wards by Thursday." (as `ward-kitchen`)
- "Why did that order need approval?"

`docker compose down` stops everything and keeps the data; `docker compose down -v` deletes the database too.

## Develop

Each part has its own README with setup, tests and details: [backend](saint-elmo-backend/README.md), [MCP server](saint-elmo-mcp/README.md), [frontend](saint-elmo-frontend/README.md). For day-to-day work, run only the database in Docker and the three services on the host with hot reload.

| Recipe | Does |
| --- | --- |
| `just setup` | Installs the Python dependencies and the git pre-commit hook |
| `just mcp` | Starts the MCP server on http://127.0.0.1:8001/mcp (the backend must be running) |
| `just issue-agent-token <agent> <buyer admin email>` | Issues an Agent token for a seeded agent against the dev database |
| `just up` | Builds and starts the whole stack in Docker |
| `just compose-token <agent> <buyer admin email>` | Issues an Agent token from the running Docker stack |

## Valio Aimo API

Valio Aimo's mock API is described in [`openapi.json`](openapi.json). It answers price and availability only; it takes no quotes or orders, which is why Saint Elmo builds those itself.

Everything under `/api` requires an `X-API-Key` header, with the key from the Junction platform:

```sh
curl -H "X-API-Key: <api key from platform>" https://junction26.valioaimo.fi/api/ping
```
