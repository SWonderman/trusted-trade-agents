# Saint Elmo

Saint Elmo is the gateway that lets a buyer organisation's autonomous purchasing agents find, compare and order products from Valio Aimo, within limits a human sets, with every decision explainable afterwards.

## Parties

**Buyer organisation**:
A Valio Aimo customer (hotel chain, school, hospital kitchen) that runs agents and owns their mandates, orders and audit trail.
_Avoid_: Tenant (in conversation), client, customer account

**Agent**:
A piece of software acting for a buyer organisation on one task, identified by its agent tokens and bound to exactly one mandate. Always untrusted.
_Avoid_: Bot, assistant, client

**Agent token**:
A signed, expiring credential a buyer admin issues for an agent, naming the agent, its buyer organisation, its scopes and its mandate. It identifies the agent's authority and never carries it: the mandate Saint Elmo holds is what is enforced.
_Avoid_: Agent key, API key (ambiguous with the Valio Aimo API key), JWT (in conversation)

**Buyer admin**:
A human in the buyer organisation who manages its agents, their mandates and their agent tokens.
_Avoid_: Admin (on its own), operator

**Approver**:
A human in the buyer organisation who signs off orders that need approval.
_Avoid_: Admin, reviewer

## Catalog

**Product**:
One orderable Valio Aimo item, identified by its product code.
_Avoid_: SKU, article, item

**Product code**:
Valio Aimo's identifier for a product, shared by the static catalog and the Valio Aimo API.
_Avoid_: Product id, SKU

**Vocabulary**:
The set of claim, diet, label, allergen and category codes that at least one product actually uses.
_Avoid_: Taxonomy, enums

**Curated substitute**:
A replacement product that Valio Aimo itself lists for a product.
_Avoid_: Alternative, official substitute

## Quantities

**Sales unit**:
The unit a product is ordered and priced in (e.g. `KI`, a case), which may hold several base units.
_Avoid_: Unit (on its own), pack

**Buyer unit**:
The unit the buyer thinks in when stating a need, such as litres or kilograms.
_Avoid_: Requested unit, customer unit

**Lot size**:
The step that an ordered quantity of a product must be a multiple of.
_Avoid_: Minimum order quantity, MOQ

**Conversion**:
The stated relation between a buyer unit and a product's sales unit (e.g. 1 KI ≈ 20 L), shown with every quantity it was used for.
_Avoid_: Normalisation (in output), unit maths

## Inquiry and commitment

**Offer**:
Live price and availability for one product on a delivery date, with provenance and an expiry. Binding on nothing.
_Avoid_: Quote (an offer is not a quote), price check

**Quote**:
A priced basket of quote lines that the policy has judged against the agent's mandate, valid until it expires.
_Avoid_: Cart, basket, offer

**Quote line**:
One product and quantity in a quote, optionally marked as a substitute for another product.
_Avoid_: Item, row

**Order**:
A commitment made from exactly one quote, re-checked against live data at the moment it is placed.
_Avoid_: Purchase, transaction

**Shortfall**:
The part of a quote line that cannot be delivered as asked: too little stock, too late, or not at all.
_Avoid_: Stock-out (a stock-out is one kind of shortfall), gap

**Substitute**:
A product the agent proposes instead of one it cannot get, judged by the same mandate as the original.
_Avoid_: Alternative, replacement, swap

## Control

**Mandate**:
The limits a buyer organisation sets for one agent: spend, assortment, requirements, substitution and delivery rules. Set by a human, readable by the agent, never changeable by it.
_Avoid_: Policy (the policy applies the mandate), permissions, rules

**Scope**:
A coarse capability on an agent token saying which kinds of operation the agent may call at all, such as reading the catalog or placing orders, independent of any mandate limit.
_Avoid_: Permission, privilege, role

**Revocation**:
A buyer admin withdrawing an agent token, or every token of an agent, so that it is refused from the next request on.

**Policy**:
The deterministic judgement of a quote or order against a mandate, giving a policy outcome and reason codes.
_Avoid_: Guardrails (in technical text), rules engine

**Policy outcome**:
One of auto-approve, needs-human or reject.
_Avoid_: Decision, verdict

**Reason code**:
A stable, machine-readable code stating one reason behind a policy outcome or shortfall.
_Avoid_: Error code (errors are failures; reason codes are answers)

**Period spend**:
What an agent's orders have committed within the mandate's current spend period, counted from Saint Elmo's own order book.
_Avoid_: Budget used

## Explanation

**Buyer request**:
The need as the buyer stated it to their agent, e.g. "1,000 litres of lactose-free milk by Monday". It is kept with the quote and never affects the policy.
_Avoid_: Prompt, task, intent

**Rationale**:
The agent's own explanation of why it chose what it chose. It is shown to approvers and kept in the audit trail, and never affects the policy.
_Avoid_: Justification, reasoning, explanation (on its own)

**Provenance**:
Where a claim came from, when, how long it holds and how certain it is (e.g. a product-group average versus a manufacturer declaration).
_Avoid_: Source, metadata

**Audit trail**:
The append-only record of what every agent and human did and why, readable by both the buyer organisation and Valio Aimo.
_Avoid_: Log (on its own), history
