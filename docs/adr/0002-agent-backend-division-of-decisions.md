# What the agent decides and what the backend decides

The agent interprets and chooses. The backend converts, checks and enforces. Concretely:

- **Dates: the agent resolves them.** "By Monday" becomes `deliverBy: 2026-11-16` on the agent side. The backend states in every response the date it evaluated against, together with `closingTime`, so a misreading shows up in the response and in the audit trail. Parsing relative dates on the backend would need timezone and delivery-weekday rules we don't have. The one default the backend picks is for ranking substitutes without a `deliverBy`: tomorrow in Europe/Helsinki, a fixed rule rather than a reading of the agent's words, echoed as `deliverBy` like any other evaluated date.
- **Quantities: the backend converts them.** The agent states quantities in buyer units (`1000 L`). The backend converts to sales units, rounds up to the lot size and returns the conversion it used. LLMs do unit arithmetic badly, and the conversion has to be deterministic and auditable.
- **Substitution: the agent decides.** The backend reports shortfalls with reason codes and ranks substitutes on request, but never swaps a product on its own. Choosing a substitute is a decision, so it belongs to the agent, within the mandate and visible in the audit trail.
- **The mandate is fully visible to the agent.** Hiding thresholds would only make the agent's pre-checks worse. Gaming by splitting orders is stopped by a period spend cap computed from our own order book, not by secrecy. Buyer-side checks are convenience; the backend's policy is the enforcement.
- **Free text from the agent never influences a decision.** `buyerRequest` and `rationale` are stored and shown to approvers and in the audit trail. The policy reads only structured fields.
- **One quote gives at most one order.** The quote id is the idempotency key for placing an order, so an agent retrying after a timeout can't order twice.
