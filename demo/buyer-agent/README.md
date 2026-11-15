# Buyer agent demo

Start `claude` in this folder and it becomes a buyer's purchasing agent, connected to Saint Elmo over MCP. It sees only the gateway: the repo's dev instructions and source code stay out of its context.

- `.mcp.json` declares one server, `saint-elmo`, at `$SAINT_ELMO_MCP_URL` (default `http://localhost:8001/mcp`), sending `$SAINT_ELMO_AGENT_KEY` as the `X-Agent-Key` header. No token is committed.
- `CLAUDE.md` is the persona. It names no organisation: the Agent token decides who the agent buys for.
- `.claude/settings.json` keeps Claude Code from loading any `CLAUDE.md` outside this folder (`claudeMdExcludes`). That covers the repo-root one, and a personal `~/.claude/CLAUDE.md` too.

## Prerequisites

1. The backend's `.env` (`saint-elmo-backend/.env`, from `.env.example`) sets:
   - `VALIO_AIMO_API_URL` and `VALIO_AIMO_API_KEY`, from the challenge portal. Without them every offer, quote and order fails with `VALIO_AIMO_UNAVAILABLE`.
   - `OFFERS_IGNORE_CLOSING_TIME=true`. Without it, lines past the order closing time are rejected for `CLOSING_TIME_PASSED`.
2. The database is seeded and the backend is running:

   ```sh
   cd saint-elmo-backend
   docker compose up -d db
   uv run python -m saint_elmo_backend.db.seeders.runner
   uv run uvicorn saint_elmo_backend.main:app --reload   # serves :8000
   ```

3. The MCP server is running. From the repo root:

   ```sh
   just mcp
   ```

## Run

Get an Agent token, either from the console (Agents → an agent → Tokens → Issue, which also shows the commands below with the token filled in) or from the repo root:

```sh
just issue-agent-token dairy-restock buyer.admin@aurora-hotels.example        # milk scenario
just issue-agent-token ward-kitchen buyer.admin@kuusikko-hospital.example     # allergen scenario
```

Then, in this folder:

```sh
export SAINT_ELMO_AGENT_KEY=<agent token>
claude
```

Approve the `saint-elmo` server when Claude Code asks, on first launch. `/mcp` shows it connected and lists its tools.

Without `SAINT_ELMO_AGENT_KEY`, tool calls fail with `MISSING_AGENT_KEY`. To use another MCP server, set `SAINT_ELMO_MCP_URL` before starting `claude`.

## Sample prompts

Milk scenario (`dairy-restock`, Aurora Hotels: lactose-free dairy only, orders over €1,500 need approval):

- "We need 1,000 litres of lactose-free milk by Monday."
- "What happens if there isn't enough in stock? Show me the substitutes."
- "Why did that order need approval?"

Hospital allergen scenario (`ward-kitchen`, Kuusikko Hospital Kitchen: nothing containing milk or gluten, declared free only, every substitute needs approval):

- "Order 40 kilos of oat flakes for porridge on the wards by Thursday."
- "Find a yoghurt we can serve on the wards next week."
- "Is that product actually declared free of milk, or just missing data?"
