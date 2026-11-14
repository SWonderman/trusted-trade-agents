# Saint Elmo frontend

The human side of Saint Elmo: a marketing page, and **agent control**, the console where a buyer organisation approves what its purchasing agents can't decide alone, sets their mandates and keys, and reads the audit trail. Valio Aimo staff get a read-only cross-customer view with demo controls.

SvelteKit 3 (Svelte 5 runes), Tailwind CSS 4 and `adapter-node`. It runs as a backend-for-frontend, as described in `../design.md` §3.4: the browser only talks to SvelteKit, and SvelteKit's server side talks to FastAPI.

## Run it

```sh
npm install
cp .env.example .env        # API_MODE=mock works without the backend
SESSION_COOKIE_SECURE=false npm run dev
```

Open <http://localhost:5173>. In mock mode the login page lists the demo accounts; every password is `demo`.

| Account                 | Sees                                                             |
| ----------------------- | ---------------------------------------------------------------- |
| `aino@kajohotels.demo`  | Kajo Hotels: approval inbox, `dairy-restock` and `event-planner` |
| `mikael@merikoski.demo` | Merikoski Hospital kitchen: `ward-kitchen` with allergen rules   |
| `satu@aimo-ops.demo`    | Valio Aimo operations: oversight feed and demo controls          |

Restart `npm run dev` after adding new route or component files. Otherwise the dev server can serve a stylesheet without their Tailwind classes.

## Screens

| Route                                         | What it's for                                                                                                                          |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `/`                                           | Marketing page (prerendered)                                                                                                           |
| `/login`                                      | Sign-in with environment and session status                                                                                            |
| `/inbox`, `/inbox/[orderId]`                  | Approval inbox: the policy's reason codes next to the agent's note, unit conversions, live offer checks, approve or reject with a note |
| `/agents`, `/agents/[agentId]`, `/agents/new` | Agents and mandates: spend, requirements, substitution rules; issue a key (shown once), revoke, disable                                |
| `/audit`                                      | Append-only, hash-chained audit trail, filterable by agent, order, tool call or outcome; `/audit/export.json` downloads it             |
| `/oversight`                                  | Valio Aimo staff only: cross-customer activity, stock and price overrides, simulate an agent order                                     |

## Connecting to the backend

Pages never call the backend directly. Server `load` functions and form actions use `api` from `src/lib/server/api`, which implements one interface (`client.ts`) in two ways:

- `mock/`: in-memory fixtures that follow the demo seed in issue #11. Actions really change state, and every read is filtered by organisation, as row-level security will do.
- `http/`: `fetch` to `BACKEND_URL` with the user's JWT as a bearer token. It turns the backend's `{ error: { code, message } }` envelope into form errors.

`API_MODE` picks the implementation, and `API_MODE_ORDERS`, `API_MODE_AGENTS` and the other per-area variables override it, so real endpoints can be switched on one at a time as issues #11, #13, #15 and #22 land. The shared types in `src/lib/api/types.ts` mirror those issues; replace them with types generated from FastAPI's `/openapi.json` once it publishes these routes.

## Checks

```sh
npm run check    # svelte-check
npm run lint     # prettier + eslint
npm run build && PORT=3000 ORIGIN=http://localhost:3000 node build
```

## Image credits

Public domain, from Wikimedia Commons: Matthias Grünewald, _The Meeting of Saint Erasmus and Saint Maurice_, c. 1520–24 (Alte Pinakothek, Munich), used in the hero and cropped for the logo; Limbourg brothers, _Très Riches Heures du Duc de Berry_, September, c. 1412–16 (Musée Condé, Chantilly). The Valio Aimo logo belongs to Valio Aimo and is used for the Junction 2026 challenge.
