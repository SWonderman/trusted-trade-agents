# Saint Elmo

A gateway that lets a buyer organisation's autonomous purchasing agents search, quote and order from Valio Aimo, within limits set by humans at that organisation.

## Actors

**Organisation**:
A Valio Aimo customer (hotel chain, hospital kitchen) whose people and agents use the gateway; the unit of data isolation.
_Avoid_: Tenant (in domain talk), customer account, client

**User**:
A human at an Organisation who manages agents and mandates and signs off escalated orders.
_Avoid_: Admin, operator

**Agent**:
An external, untrusted purchasing program acting for an Organisation on a specific job, such as dairy restocking.
_Avoid_: Bot, client, assistant

## Authority

**Mandate**:
The business limits an Agent's quotes and orders are checked against: spend, assortment, required claims and allergen exclusions, substitution and delivery rules. Set by a User, held by the gateway, and read-only to the Agent.
_Avoid_: Policy, rules, permissions, privileges

**Scope**:
A coarse capability saying which kinds of operation an Agent may call at all, such as reading the catalog or placing orders, independent of any Mandate limit.
_Avoid_: Permission, privilege, role

**Agent token**:
A signed, expiring credential that a User issues for an Agent, naming that Agent, its Organisation, its Scopes and its Mandate. It identifies the Agent's authority and never carries it: the Mandate held by the gateway is what is enforced.
_Avoid_: API key, agent key, JWT (in domain talk)

**Revocation**:
A User withdrawing an Agent token, or every token of an Agent, so that it is refused from the next request on.
