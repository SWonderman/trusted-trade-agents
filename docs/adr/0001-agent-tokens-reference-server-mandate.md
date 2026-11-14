# Agent tokens reference the Mandate, they don't carry it

Agents authenticate with an Agent token: an EdDSA-signed JWT, issued by a User through the frontend, with `sub` (agent id), `org_id`, `scope`, `mandate_id`, `jti` and `exp`. Its public key is published as a JWKS. The token names the Mandate but does not embed its limits. The policy engine always enforces the Mandate as currently held by the gateway, and checks the token's `jti` on every request so that Revocation is immediate.

We considered putting the full Mandate in the token so the gateway could enforce it without state, and rejected that. Period spend limits need order history from the database anyway. Mandate edits and Revocation must take effect on the next request. And a token that disagrees with the database would leave two sources of truth, which breaks reproducible, deterministic audit. We also rejected opaque API keys: a signed JWT with a published JWKS is an open standard, verifiable by third parties, and the same shape as the OAuth 2.1 access tokens the MCP authorization flow would issue later.

## Consequences

- Every authenticated agent request costs a database lookup (credential status, Mandate). We pay that anyway for RLS tenant context and policy checks.
- Editing a Mandate affects all live tokens of that Agent at once. Audit events record which mandate version was applied.
- There is no "approve" Scope. Approving is restricted to User authentication, so no Agent token can grant it.
- User session JWTs stay HS256 with a separate secret, so an Agent token can never pass as a user session.
