# Saint Elmo

A gateway through which external purchasing agents find, quote and order Valio Aimo products within a mandate that a person at the buyer organisation sets. Agents connect over MCP (`saint-elmo-mcp`) or REST (`saint-elmo-backend`); people manage agents, keys and approvals in the console (`saint-elmo-frontend`).

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

`docker compose down` stops everything and keeps the data; `docker compose down -v` deletes the database too.

## Valio Aimo API documentation

File: openapi.json

### Authentication

Everything under /api requires an `X-API-Key` header. API key can be found on the Junction platform

`curl -H "X-API-Key: <api key from platform>" https://junction26.valioaimo.fi/api/ping`
