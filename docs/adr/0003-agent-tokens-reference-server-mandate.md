# Agent tokens reference the mandate, they don't carry it

Agents authenticate with an agent token: an EdDSA-signed JWT, issued by a buyer admin, with `sub` (agent id), `org_id`, `scope`, `mandate_id`, `jti` and `exp`. Its public key is published as a JWKS. The token names the mandate but does not embed its limits. The policy always applies the mandate as Saint Elmo currently holds it, and every request checks the token's `jti` so that revocation is immediate. This makes concrete the "agent key" that ADR 0001 forwards: the MCP server still treats it as an opaque string from `X-Agent-Key` or `Authorization: Bearer`.

We considered putting the full mandate in the token so the backend could enforce it without state, and rejected that. Period spend needs the order book anyway. Mandate edits and revocation must take effect on the next request. And a token that disagrees with the database would leave two sources of truth, which breaks a replayable audit trail. We also rejected opaque random keys: a signed JWT with a published JWKS is an open standard, verifiable by third parties, and the same shape as the OAuth 2.1 access tokens the MCP authorization flow would issue later.

## Consequences

- Every authenticated agent request costs a database lookup (credential status, mandate). We pay that anyway for the policy.
- Editing a mandate affects all live tokens of that agent at once. The mandate carries a version, and quotes and orders record which version they were judged against.
- There is no approve scope. Approving is restricted to the user scheme, so no agent token can grant it.
- User session JWTs stay HS256 with a separate secret, so an agent token can never pass as a user session.
