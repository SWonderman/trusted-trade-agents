# Saint Elmo frontend

The human side of Saint Elmo: a marketing page, and **agent control**, the console where a buyer organisation approves what its purchasing agents can't decide alone, sets their mandates and Agent tokens, looks up the catalog to write mandates, and reads the audit trail. Valio Aimo staff get a read-only cross-customer view with demo controls.

SvelteKit 3 (Svelte 5 runes), Tailwind CSS 4, [shadcn-svelte](https://shadcn-svelte.com) components (`src/lib/components/ui`, generated, Vega style) and `adapter-node`. It runs as a backend-for-frontend, as described in `../design.md` §3.4: the browser only talks to SvelteKit, and SvelteKit's server side talks to FastAPI.

## Run it

Demo data only, no backend needed:

```sh
npm install
cp .env.example .env
SESSION_COOKIE_SECURE=false npm run dev
```

With the backend for sign-in, the catalog, approvals and the audit trail (start it first, see `../saint-elmo-backend/README.md`), set in `.env`:

```sh
API_MODE=mock
API_MODE_AUTH=http
API_MODE_CATALOG=http
API_MODE_ORDERS=http
API_MODE_AUDIT=http
BACKEND_URL=http://localhost:8000
SESSION_COOKIE_SECURE=false
```

To see an approval end to end:

1. Issue an Agent token for a seeded agent: `just issue-agent-token dairy-restock buyer.admin@aurora-hotels.example`.
2. Give it to an MCP client (`../saint-elmo-mcp`) and ask for something over the agent's auto-approve limit, e.g. 1,000 L of lactose-free milk for next week. The agent quotes, then places the order; its mandate sends it to a person.
3. Sign in as `buyer.admin@aurora-hotels.example`. The order appears under **Approvals** within seconds (the console polls), with the policy's reason codes, the lines and their conversions, shortfalls, substitutes, the buyer's request and the agent's rationale.
4. Approve it, or reject it with a note. Approving re-checks live price, stock and closing time first: the order is placed, rejected if a hard rule now fails (e.g. `CLOSING_TIME_PASSED`), or left waiting with its new reasons and total if something changed that you haven't seen. The page says which.

The backend quotes from the live Valio Aimo API, so it needs `VALIO_AIMO_API_URL` and `VALIO_AIMO_API_KEY` for steps 2 to 4.

Open <http://localhost:5173>. The demo accounts match the backend seed, so they work in both setups; every password is `saint-elmo-demo`.

| Account                                 | Sees                                                                |
| --------------------------------------- | ------------------------------------------------------------------- |
| `buyer.admin@aurora-hotels.example`     | Aurora Hotels: approvals, `dairy-restock` and `event-planner`       |
| `buyer.admin@kuusikko-hospital.example` | Kuusikko Hospital Kitchen: `ward-kitchen` with allergen rules       |
| `ops@valio-aimo.example`                | Valio Aimo operations: oversight feed and demo controls (mock only) |

Restart `npm run dev` after adding new route or component files, or after changing `.env`.

## Design

One token system in `src/routes/layout.css` serves both halves. Its palette comes from the Grünewald panel the brand is cut from: lapis (primary), gold leaf (accent, used sparingly), vermilion (destructive and hard rejections) and vellum, on warm neutrals, with a light and a dark theme (`mode-watcher`, `.dark` class). Type: EB Garamond for display (a Renaissance Garamond, set tight), Inter for the UI, IBM Plex Mono for codes.

- The marketing page uses the palette at full strength: a fixed night-lapis and vellum page, the painting in an arch.
- The console is a quieter SaaS layout: inset sidebar, page headers in Garamond, shadcn components. Each page header says whether its data is **Live** (backend) or **Demo data** (mock), and the sidebar lists which areas are live.

Add more shadcn components with `npx shadcn-svelte@1.8.1 add <name>`, then `npm run format`.

## Screens

| Route                                         | What it's for                                                                                                                                                            |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/`                                           | Marketing page (prerendered)                                                                                                                                             |
| `/login`                                      | Sign-in, against the backend with `API_MODE_AUTH=http`                                                                                                                   |
| `/inbox`, `/inbox/[orderId]`                  | Approvals: the policy's reason codes next to the agent's rationale, unit conversions, live offer checks, approve or reject with a note                                   |
| `/agents`, `/agents/[agentId]`, `/agents/new` | Agents and mandates: spend, requirements, substitution rules; issue an Agent token (shown once), revoke, disable                                                         |
| `/catalog`, `/catalog/[code]`                 | Read-only catalog, a reference for writing mandates: search by claim, allergen and category; product detail with allergens, nutrition, packaging and curated substitutes |
| `/audit`                                      | Append-only audit trail, filterable by agent, order or quote, event type or outcome; `/audit/export.json` downloads it                                                   |
| `/oversight`                                  | Valio Aimo staff only: cross-customer activity, stock and price overrides, simulate an agent order                                                                       |

## Connecting to the backend

Pages never call the backend directly. Server `load` functions and form actions use `api` from `src/lib/server/api`, which implements one interface (`client.ts`) in two ways:

- `mock/`: in-memory fixtures that follow the backend's demo seed (same organisations, people, agents and mandates; order lines use real catalog products). Actions really change state, until the server restarts. Every read is filtered by the caller's organisation, matched by id or, for a backend session, by name.
- `http/`: `fetch` to `BACKEND_URL` with the user's JWT as a bearer token. Sign-in is the OAuth 2.0 password grant on `/api/v1/auth/token`, then `/api/v1/auth/me`. The backend's `{ error: { code, message } }` envelope becomes form errors.

`API_MODE` picks the implementation, and `API_MODE_AUTH`, `API_MODE_CATALOG`, `API_MODE_ORDERS`, `API_MODE_AGENTS`, `API_MODE_AUDIT` and `API_MODE_OVERSIGHT` override it per area, so real endpoints can be switched on one at a time as issues #13, #15 and #22 land. Any `http` area needs `API_MODE_AUTH=http`, since the backend only accepts sessions it signed; the server refuses to start otherwise.

Live today: sign-in (`auth`), the catalog (`catalog`), approvals (`orders`) and the audit trail (`audit`). Agents and oversight still answer from the mock.

Approvals read every order in `PENDING_APPROVAL` (`GET /api/v1/orders?status=`, page by page) and the 100 most recent orders, open one with `GET /api/v1/orders/{id}`, and decide with `POST /api/v1/orders/{id}/approve` or `/reject`. The `Order` type is the backend's `OrderResponse`, and the mock answers in the same shape, UUID ids included; ids show by their first eight characters. Another organisation's order, or an id that isn't a UUID, is a 404. An approval comes back `PLACED`, `REJECTED` by the re-check, or still `PENDING_APPROVAL`; the page stays on the order for the last two and says why. A 409 `ORDER_NOT_PENDING` (decided elsewhere) reloads it, and a 403, or a re-check that can't run (Valio Aimo unavailable, no mandate, a product gone from the catalog), is explained in place. The frontend asks for a note to reject, though the backend accepts none. A substitute's trade-offs come from the order: its line's reasons, and its price and delivery against the original's when the original is on the order too. The catalog adds vendors and declared claims, diets and labels when it has both products. The mandate panel is left out while agents answer from the mock, which doesn't know the backend's agent ids. The mock's re-check mirrors the backend's: a passed closing time rejects, and an active `PRICE_CHANGE` scenario keeps the order waiting at its higher total.

The live audit trail reads `GET /api/v1/audit-events` (up to 1,000 events, newest first) and, when filtered by an order, `GET /api/v1/orders/{id}/trail`, which also brings the order's quotes and substitute requests; a quote id falls back to the events about that quote. The backend filters by agent and event type, the frontend by policy outcome. Two differences from the mock: the backend records decisions and commitments, not every tool call, and its events carry no hash chain. Each event's recorded `payload` is included in the JSON export. Order ids in the trail are the backend's, so their links into `/inbox` resolve when orders are live too. The oversight feed stays on the mock: the backend's audit trail is scoped to the caller's own buyer organisation and has no cross-customer read for Valio Aimo staff yet.

Types for routes the backend serves come from its OpenAPI schema: `npm run gen:api` (with the backend running, `BACKEND_URL` defaults to `http://localhost:8000`) regenerates `src/lib/api/backend.d.ts`, and `src/lib/api/types.ts` re-exports them under short names. The rest of `types.ts` mirrors the open issues until those routes exist.

Live offers (`POST /api/v1/offers`) stay agent-only by design: Saint Elmo is first a gateway for agents, and the console is where people manage those agents, their Agent tokens and mandates, not where they shop.

## Checks

```sh
npm run check    # svelte-check
npm run lint     # prettier + eslint
npm run build && PORT=3000 ORIGIN=http://localhost:3000 node build
```

## Image credits

Public domain, from Wikimedia Commons: Matthias Grünewald, _The Meeting of Saint Erasmus and Saint Maurice_, c. 1520–24 (Alte Pinakothek, Munich), used in the hero and cropped for the logo; Limbourg brothers, _Très Riches Heures du Duc de Berry_, September, c. 1412–16 (Musée Condé, Chantilly). The Valio Aimo logo belongs to Valio Aimo and is used for the Junction 2026 challenge.
