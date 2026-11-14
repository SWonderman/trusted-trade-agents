# A buyer organisation is a plain foreign key, with no tenant isolation in the demo

Every agent, user, mandate, quote, order and audit event belongs to one buyer organisation through an ordinary `org_id` column. An agent token carries it as the `org_id` claim, a user session resolves to it, and the request principal holds it. Services that read or change buyer-owned data take the buyer organisation from the principal as a required argument and filter by it in the query. The client never sends it. There is no Postgres row-level security, no separate runtime database role and no per-request tenant setting.

A user belongs to exactly one buyer organisation and has one role (buyer admin or approver). Users are seeded, and the only account feature is login.

The challenge scores the end-to-end flow, the guardrails and the audit trail. Nothing in it asks for buyer organisations to be isolated from one another, and the demo runs two buyer organisations that we seed and operate ourselves. Row-level security would cost hand-written policies on every table, a second database role, a test harness that connects as that role, and an ordering problem in agent token verification (the credential row can only be read after the tenant is set). That time goes to agent tokens, the mandate and the policy instead.

## Considered options

- **Postgres row-level security, as first planned in design §3.7:** rejected for the demo and kept as the production step. The data model stays ready for it, because every buyer-owned table already has the `org_id` column a policy would read.
- **No buyer organisation at all (a single implicit buyer):** rejected. It would save one table but lose the two named buyers behind the demo scenarios (the hotel chain and the hospital kitchen), the Valio Aimo customer number passed to the mock API, the `org_id` claim from ADR 0003, and Valio Aimo's view of the audit trail across buyers.
- **Porting a full account system (memberships, users in several organisations, signup, invitations, email verification, refresh tokens):** rejected. None of it is part of the demo.

## Consequences

- Isolation between buyer organisations depends on application code. If a service forgets the `org_id` filter, one buyer organisation's data is visible to another, and nothing in the database stops it. Passing the buyer organisation as a required argument, not as ambient request state, keeps the filter visible in every call, and the cross-organisation tests stay as HTTP-level tests.
- Moving to production means adding the row-level security policies and the runtime role on top of the existing columns, with no change to the data model.
- User sessions are short-lived HS256 tokens with no refresh. A user logs in again when one expires.
- This amends design §3.7 and the row-level-security parts of #7, #11, #14, #22 and #23.
