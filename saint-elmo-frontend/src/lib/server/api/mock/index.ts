import { randomBytes, randomUUID } from 'node:crypto';
import type {
	AgentKey,
	AgentSummary,
	AuditEvent,
	KeyPreset,
	Mandate,
	Order,
	OversightEvent,
	PolicyReason,
	ScenarioOverride,
	SessionUser
} from '#lib/api/types.js';
import { ApiError, type Caller, type SaintElmoApi } from '../client';
import {
	AGENTS,
	KEYS,
	MANDATES,
	ORGS,
	SCENARIOS,
	USERS,
	buildOrders,
	daysFromNow,
	judged,
	minutesAgo,
	withTax,
	type MockOrder
} from './fixtures';
import { agentOf } from '#lib/audit.js';
import { shortId } from '#lib/format.js';
import { mockCatalog } from './catalog';

/**
 * In-memory stand-in for the FastAPI backend. State lives on globalThis so it
 * survives Vite hot reloads; it resets when the dev server restarts.
 *
 * Tenant isolation is mirrored here the way Postgres RLS will enforce it:
 * every read and write is filtered by the caller's organisation.
 */

type AgentRow = (typeof AGENTS)[number] & { mandate: Mandate };

interface Store {
	orders: MockOrder[];
	agents: AgentRow[];
	keys: Record<string, AgentKey[]>;
	/** Oldest first, each filed under the buyer organisation it belongs to. */
	audit: OversightEvent[];
	scenarios: ScenarioOverride[];
}

const PRESET_SCOPES: Record<KeyPreset, string[]> = {
	RESEARCH_ONLY: ['catalog:read', 'offers:read', 'mandate:read', 'order:read'],
	PURCHASING: [
		'catalog:read',
		'offers:read',
		'mandate:read',
		'quote:create',
		'order:place',
		'order:read'
	]
};

const g = globalThis as typeof globalThis & { __saintElmoMock?: Store };

function store(): Store {
	if (!g.__saintElmoMock) g.__saintElmoMock = seed();
	return g.__saintElmoMock;
}

// --- Audit trail -------------------------------------------------------------

const SYSTEM = { kind: 'system', id: null, name: 'system' } as const;

/** Records an event as the backend does: what it is about, who acted and its data. */
function append(
	s: Store,
	event: Pick<OversightEvent, 'at' | 'type' | 'actor' | 'summary' | 'organisationId'> &
		Partial<Pick<OversightEvent, 'subjectId' | 'outcome' | 'reasonCodes' | 'payload'>>
) {
	s.audit.push({
		id: randomUUID(),
		subjectId: null,
		outcome: null,
		reasonCodes: null,
		payload: {},
		...event,
		organisationName: orgName(event.organisationId)
	});
}

function orgName(id: string) {
	return ORGS.find((o) => o.id === id)?.name ?? id;
}

/** The signed-in person, as the actor of an event. */
const userActor = (caller: Caller) =>
	({ kind: 'user', id: caller.user.id, name: caller.user.name }) as const;

/** The reason codes of the hard rules a judgement broke. */
const rejectCodes = (policy: MockOrder['policy']) =>
	policy.reasons.filter((r) => r.severity === 'REJECT').map((r) => r.code);

/** Newest first, also among events recorded at the same moment. */
const newestFirst = (events: OversightEvent[]) =>
	events.toReversed().toSorted((a, b) => b.at.localeCompare(a.at));

/** "needs a human (the order total is over the auto-approve limit)", as the backend words a verdict. */
function verdict(policy: MockOrder['policy']) {
	if (policy.outcome === 'AUTO_APPROVE') return 'within the mandate';
	const first = policy.reasons
		.find((r) => r.severity === policy.outcome)
		?.message.split('. ')[0]
		.replace(/\.$/, '');
	const why = first ? ` (${first[0].toLowerCase()}${first.slice(1)})` : '';
	return (policy.outcome === 'REJECT' ? 'rejected' : 'needs a human') + why;
}

/** The trail an agent leaves placing an order: substitutes, the quote, the request, the re-check. */
function seedOrderTrail(s: Store, o: MockOrder) {
	const t0 = new Date(o.createdAt).getTime();
	const at = (minBefore: number) => new Date(t0 - minBefore * 60_000).toISOString();
	const agent = { kind: 'agent', id: o.agent.id, name: o.agent.name } as const;
	const base = { organisationId: o.organisationId, actor: agent };
	const total = `€${o.totals.net.toLocaleString('en-GB', { minimumFractionDigits: 2 })}`;
	const policy = { outcome: o.policy.outcome, mandateVersion: o.policy.mandateVersion };
	const reasonCodes = o.policy.reasons.map((r) => r.code);

	for (const [i, sub] of o.lines.filter((l) => l.substitutesFor).entries()) {
		append(s, {
			...base,
			at: at(3 + i),
			type: 'SUBSTITUTES_REQUESTED',
			summary: `${o.agent.name} asked for substitutes for ${sub.substitutesFor} and got 1 candidate, best ${sub.productCode}`,
			reasonCodes: sub.reasons.map((r) => r.code),
			payload: { productCode: sub.substitutesFor, candidates: [{ productCode: sub.productCode }] }
		});
	}
	append(s, {
		...base,
		at: at(2),
		type: 'QUOTE_CREATED',
		subjectId: o.quoteId,
		summary: `${o.agent.name} quoted ${o.lines.length} ${o.lines.length === 1 ? 'line' : 'lines'} for ${total}: ${verdict(o.policy)}`,
		outcome: o.policy.outcome,
		reasonCodes,
		payload: {
			quoteId: o.quoteId,
			request: {
				deliverBy: o.deliverBy,
				lines: o.lines.map((l) => ({
					productCode: l.productCode,
					quantity: l.quantity?.requested.value ?? null,
					unit: l.quantity?.requested.unit ?? null,
					substitutesFor: l.substitutesFor
				})),
				buyerRequest: o.buyerRequest,
				rationale: o.rationale,
				previousQuoteId: null
			},
			policy,
			totals: { net: o.totals.net }
		}
	});
	append(s, {
		...base,
		at: at(1),
		type: 'ORDER_REQUESTED',
		subjectId: o.orderId,
		summary: `${o.agent.name} asked to place an order from quote ${shortId(o.quoteId)}`,
		payload: { quoteId: o.quoteId }
	});
	append(s, {
		...base,
		at: o.createdAt,
		type: 'ORDER_RECHECKED',
		subjectId: o.orderId,
		summary: `${o.agent.name} re-checked the order on live data: ${total}, ${verdict(o.policy)}`,
		outcome: o.policy.outcome,
		reasonCodes,
		payload: { policy, totals: { net: o.totals.net } }
	});
	for (const h of o.statusHistory) {
		const event = { ...base, at: h.at, subjectId: o.orderId };
		const person = h.by.startsWith('user:')
			? ({ kind: 'user', id: null, name: h.by.slice('user:'.length) } as const)
			: null;
		if (h.status === 'PENDING_APPROVAL') {
			append(s, {
				...event,
				type: 'ORDER_PENDING_APPROVAL',
				summary: 'The order is waiting for a human to approve it',
				outcome: 'NEEDS_HUMAN',
				reasonCodes
			});
		} else if (h.status === 'CONFIRMED') {
			append(s, {
				...event,
				type: 'ORDER_CONFIRMED',
				summary: 'The order was confirmed: the policy approved it automatically',
				outcome: 'AUTO_APPROVE'
			});
		} else if (h.status === 'APPROVED' && person) {
			append(s, {
				...event,
				actor: person,
				type: 'ORDER_APPROVED',
				summary: `${person.name} approved the order`
			});
		} else if (h.status === 'PLACED') {
			append(s, {
				...event,
				actor: SYSTEM,
				type: 'ORDER_PLACED',
				summary: 'The order was placed in the order book'
			});
		} else if (h.status === 'REJECTED') {
			append(
				s,
				person
					? {
							...event,
							actor: person,
							type: 'ORDER_REJECTED_BY_HUMAN',
							summary: `${person.name} rejected the order`
						}
					: {
							...event,
							type: 'ORDER_REJECTED',
							summary: 'The policy rejected the order',
							outcome: 'REJECT',
							reasonCodes: rejectCodes(o.policy)
						}
			);
		}
	}
}

function seed(): Store {
	const s: Store = {
		orders: buildOrders(),
		agents: AGENTS.map((a) => ({ ...a, mandate: structuredClone(MANDATES[a.id]) })),
		keys: structuredClone(KEYS),
		audit: [],
		scenarios: structuredClone(SCENARIOS)
	};
	append(s, {
		at: minutesAgo(60 * 24 * 3),
		organisationId: 'org-aurora',
		actor: { kind: 'user', id: 'u-helmi', name: 'Helmi Virtanen' },
		type: 'AGENT_TOKEN_ISSUED',
		subjectId: 'agt-dairy',
		summary: 'Helmi Virtanen issued the Agent token "laptop" to dairy-restock, purchasing',
		payload: { label: 'laptop', preset: 'PURCHASING', scopes: PRESET_SCOPES.PURCHASING }
	});
	const chronological = [...s.orders].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
	for (const o of chronological) seedOrderTrail(s, o);
	return s;
}

// --- Helpers ----------------------------------------------------------------

/**
 * The demo organisation the caller belongs to. Matched by id, or by name when the
 * session comes from the real backend (API_MODE_AUTH=http), whose seed uses the same
 * organisation names but its own ids. That keeps not-yet-built areas on demo data
 * while sign-in is real.
 */
function demoOrgOf(caller: Caller) {
	const org = caller.user.organisation;
	if (!org) return null;
	return ORGS.find((o) => o.id === org.id) ?? ORGS.find((o) => o.name === org.name) ?? null;
}

function orgOf(caller: Caller) {
	return demoOrgOf(caller)?.id ?? null;
}

function visible<T extends { organisationId: string }>(caller: Caller, rows: T[]) {
	const org = orgOf(caller);
	// Valio Aimo staff read across customers; everyone else sees only their own.
	return caller.user.role === 'AIMO_STAFF' ? rows : rows.filter((r) => r.organisationId === org);
}

function requireBuyer(caller: Caller) {
	const org = demoOrgOf(caller);
	if (caller.user.role === 'AIMO_STAFF' || !org) {
		throw new ApiError(
			403,
			'PERMISSION_DENIED',
			'Only people in the buyer organisation can do this.'
		);
	}
	return org;
}

function requireStaff(caller: Caller) {
	if (caller.user.role !== 'AIMO_STAFF') {
		throw new ApiError(403, 'PERMISSION_DENIED', 'This view is for Valio Aimo staff.');
	}
}

function periodSpend(s: Store, agent: AgentRow) {
	const committed = s.orders
		.filter(
			(o) =>
				o.agent.id === agent.id &&
				['PENDING_APPROVAL', 'APPROVED', 'PLACED', 'CONFIRMED'].includes(o.status)
		)
		.reduce((sum, o) => sum + o.totals.net, 0);
	const start = new Date();
	start.setUTCHours(0, 0, 0, 0);
	if (agent.mandate.spendPeriod === 'WEEK')
		start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7));
	else start.setUTCDate(1);
	const end = new Date(start);
	if (agent.mandate.spendPeriod === 'WEEK') end.setUTCDate(end.getUTCDate() + 7);
	else end.setUTCMonth(end.getUTCMonth() + 1);
	return {
		periodStart: start.toISOString(),
		periodEnd: end.toISOString(),
		committed: Math.round(committed * 100) / 100,
		remaining: Math.max(0, Math.round((agent.mandate.periodSpendCap - committed) * 100) / 100)
	};
}

function summary(s: Store, a: AgentRow): AgentSummary {
	return {
		id: a.id,
		name: a.name,
		purpose: a.purpose,
		status: a.status,
		mandate: a.mandate,
		periodSpend: periodSpend(s, a),
		activeKeys: (s.keys[a.id] ?? []).filter(
			(k) => !k.revokedAt && new Date(k.expiresAt).getTime() > Date.now()
		).length,
		lastActiveAt: a.lastActiveAt
	};
}

function findAgent(s: Store, caller: Caller, agentId: string) {
	const org = requireBuyer(caller);
	const a = s.agents.find((x) => x.id === agentId && x.organisationId === org.id);
	if (!a) throw new ApiError(404, 'NOT_FOUND', 'No such agent in your organisation.');
	return a;
}

/** An event as the backend returns it, without the buyer organisation the mock files it under. */
function toAuditEvent({ organisationId, organisationName, ...event }: OversightEvent): AuditEvent {
	void [organisationId, organisationName];
	return structuredClone(event);
}

/** An order as the backend returns it, without the buyer organisation the mock files it under. */
function toOrder({ organisationId, ...order }: MockOrder): Order {
	void organisationId;
	return structuredClone(order);
}

/**
 * The live re-check on approval, as the backend runs it (#15), on the data the mock
 * can change: a passed closing time rejects the order, and an active PRICE_CHANGE
 * scenario raises a line's price by 8%, which keeps the order pending at its new total.
 */
function recheck(s: Store, o: MockOrder): MockOrder {
	const now = Date.now();
	const changes = [...o.changes];
	const lines = o.lines.map((l) => {
		const line = structuredClone(l);
		const closing = line.availability?.closingTime;
		if (closing && new Date(closing).getTime() < now && line.price) {
			line.reasons = [
				...line.reasons.filter((r) => r.code !== 'CLOSING_TIME_PASSED'),
				{
					code: 'CLOSING_TIME_PASSED',
					severity: 'REJECT',
					lineRef: String(line.position),
					message: 'The order cut-off for the delivery date has passed.',
					facts: { closingTime: closing }
				}
			];
			line.outcome = 'REJECT';
		}
		const rise = s.scenarios.find(
			(sc) => sc.active && sc.kind === 'PRICE_CHANGE' && sc.productCode === line.productCode
		);
		const lineRef = String(line.position);
		const quoted = changes.find((c) => c.lineRef === lineRef && c.field === 'unitPrice');
		if (rise && line.price && line.quantity?.salesUnits && !quoted) {
			const before = line.price.perSalesUnit.net;
			const after = Math.round(before * 108) / 100;
			line.price.perSalesUnit = withTax(after);
			line.quantity.lineTotal = withTax(after * line.quantity.salesUnits);
			changes.push({ lineRef, field: 'unitPrice', quoted: before, now: after });
		}
		return line;
	});
	const orderReasons: PolicyReason[] = o.policy.reasons.filter((r) => r.lineRef === null);
	return judged({ ...o, changes }, lines, orderReasons);
}

function decide(caller: Caller, orderId: string, approve: boolean, note?: string) {
	const s = store();
	requireBuyer(caller);
	const before = visible(caller, s.orders).find((x) => x.orderId === orderId);
	if (!before) throw new ApiError(404, 'ORDER_NOT_FOUND', 'Order not found');
	if (before.status !== 'PENDING_APPROVAL') {
		throw new ApiError(
			409,
			'ORDER_NOT_PENDING',
			`The order is ${before.status}, not PENDING_APPROVAL`
		);
	}
	const by = `user:${caller.user.name}`;
	const now = new Date().toISOString();
	// A re-check on approval is credited to the approver, as the backend does.
	const base = {
		organisationId: before.organisationId,
		actor: userActor(caller),
		subjectId: before.orderId
	};
	const noted = note ? `: “${note}”` : '';
	const decided = (o: MockOrder, ...history: Order['statusHistory']): MockOrder => ({
		...o,
		status: history.at(-1)!.status,
		statusHistory: [...o.statusHistory, ...history],
		approverNote: note ?? null,
		decidedAt: now,
		checkAgainAfterSeconds: null
	});

	let o: MockOrder;
	if (approve) {
		const checked = recheck(s, before);
		const seen = new Set(before.policy.reasons.map((r) => `${r.code}:${r.lineRef}`));
		const unseen = checked.policy.reasons.filter(
			(r) => r.severity === 'NEEDS_HUMAN' && !seen.has(`${r.code}:${r.lineRef}`)
		);
		append(s, {
			...base,
			at: now,
			type: 'ORDER_RECHECKED',
			summary: `${caller.user.name} re-checked the order on live data before approving: ${verdict(checked.policy)}`,
			outcome: checked.policy.outcome,
			reasonCodes: checked.policy.reasons.map((r) => r.code),
			payload: { approval: true, totals: { net: checked.totals.net }, changes: checked.changes }
		});
		if (checked.policy.outcome === 'REJECT') {
			o = decided(checked, { status: 'REJECTED', at: now, by });
			append(s, {
				...base,
				at: now,
				type: 'ORDER_REJECTED',
				summary: 'The policy rejected the order when it was re-checked for approval',
				outcome: 'REJECT',
				reasonCodes: rejectCodes(checked.policy),
				payload: { approver: caller.user.id }
			});
		} else if (unseen.length || checked.totals.net > before.totals.net) {
			// An approval never commits more than the approver saw: decide again.
			o = checked;
		} else {
			o = decided(
				checked,
				{ status: 'APPROVED', at: now, by },
				{ status: 'PLACED', at: now, by: 'system' }
			);
			append(s, {
				...base,
				at: now,
				type: 'ORDER_APPROVED',
				summary: `${caller.user.name} approved the order${noted}`,
				payload: { note: note ?? null }
			});
			append(s, {
				...base,
				actor: SYSTEM,
				at: now,
				type: 'ORDER_PLACED',
				summary: 'The order was placed in the order book'
			});
		}
	} else {
		o = decided(before, { status: 'REJECTED', at: now, by });
		append(s, {
			...base,
			at: now,
			type: 'ORDER_REJECTED_BY_HUMAN',
			summary: `${caller.user.name} rejected the order${noted}`,
			payload: { note: note ?? null }
		});
	}
	s.orders[s.orders.indexOf(before)] = o;
	return toOrder(o);
}

// --- Session tokens (unsigned stand-ins for FastAPI's JWT) ------------------

const SESSION_MINUTES = 60;

function encodeToken(user: SessionUser) {
	const payload = {
		sub: user.id,
		org_id: user.organisation?.id ?? null,
		role: user.role,
		exp: Math.floor(Date.now() / 1000) + SESSION_MINUTES * 60
	};
	const b64 = (o: object) => Buffer.from(JSON.stringify(o)).toString('base64url');
	return `${b64({ alg: 'none', typ: 'JWT' })}.${b64(payload)}.mock`;
}

function decodeToken(token: string): { sub: string; exp: number } | null {
	try {
		return JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString());
	} catch {
		return null;
	}
}

function publicUser(u: (typeof USERS)[number]): SessionUser {
	const { id, name, email, role, organisation } = u;
	return { id, name, email, role, organisation };
}

// --- The API ----------------------------------------------------------------

export const mockApi: SaintElmoApi = {
	auth: {
		async login(email, password) {
			const u = USERS.find((x) => x.email === email.trim().toLowerCase());
			if (!u || u.password !== password) {
				throw new ApiError(
					401,
					'INVALID_CREDENTIALS',
					'That email and password don’t match an account.'
				);
			}
			const user = publicUser(u);
			return { token: encodeToken(user), user, expiresInSeconds: SESSION_MINUTES * 60 };
		},
		async session(token) {
			const claims = decodeToken(token);
			if (!claims || claims.exp * 1000 < Date.now()) return null;
			const u = USERS.find((x) => x.id === claims.sub);
			return u ? publicUser(u) : null;
		},
		async demoAccounts() {
			return USERS.map((u) => ({
				email: u.email,
				password: u.password,
				label:
					u.role === 'AIMO_STAFF' ? 'Valio Aimo operations' : `${u.organisation?.name}, buyer admin`
			}));
		}
	},

	catalog: mockCatalog,

	orders: {
		async list(caller, filter) {
			return visible(caller, store().orders)
				.filter((o) => !filter?.status || o.status === filter.status)
				.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
				.map(toOrder);
		},
		async get(caller, orderId) {
			const o = visible(caller, store().orders).find((x) => x.orderId === orderId);
			return o ? toOrder(o) : null;
		},
		async approve(caller, orderId, note) {
			return decide(caller, orderId, true, note);
		},
		async reject(caller, orderId, note) {
			return decide(caller, orderId, false, note);
		}
	},

	agents: {
		async list(caller) {
			const s = store();
			const org = requireBuyer(caller);
			return s.agents.filter((a) => a.organisationId === org.id).map((a) => summary(s, a));
		},
		async get(caller, agentId) {
			const s = store();
			try {
				return summary(s, findAgent(s, caller, agentId));
			} catch (e) {
				if (e instanceof ApiError && e.status === 404) return null;
				throw e;
			}
		},
		async create(caller, input) {
			const s = store();
			const org = requireBuyer(caller);
			if (s.agents.some((a) => a.organisationId === org.id && a.name === input.name)) {
				throw new ApiError(
					409,
					'AGENT_NAME_TAKEN',
					`An agent called ${input.name} already exists.`
				);
			}
			if (input.mandate.autoApproveUpTo > input.mandate.maxOrderTotal) {
				throw new ApiError(
					422,
					'INVALID_MANDATE',
					'The auto-approve limit can’t be above the order limit.'
				);
			}
			const row: AgentRow = {
				id: `agt-${randomBytes(3).toString('hex')}`,
				name: input.name,
				purpose: input.purpose,
				status: 'ACTIVE',
				lastActiveAt: null,
				organisationId: org.id,
				mandate: { ...input.mandate, version: 1 }
			};
			s.agents.push(row);
			s.keys[row.id] = [];
			return summary(s, row);
		},
		async setStatus(caller, agentId, status) {
			const s = store();
			const a = findAgent(s, caller, agentId);
			// The backend records disabling an agent, not enabling it again.
			if (status === 'DISABLED' && a.status !== 'DISABLED') {
				append(s, {
					at: new Date().toISOString(),
					organisationId: a.organisationId,
					actor: userActor(caller),
					type: 'AGENT_DISABLED',
					subjectId: a.id,
					summary: `${caller.user.name} disabled ${a.name}; all its Agent tokens are refused`
				});
			}
			a.status = status;
			return summary(s, a);
		},
		async listKeys(caller, agentId) {
			const s = store();
			const a = findAgent(s, caller, agentId);
			return [...(s.keys[a.id] ?? [])].sort((x, y) => y.createdAt.localeCompare(x.createdAt));
		},
		async issueKey(caller, agentId, input) {
			const s = store();
			const a = findAgent(s, caller, agentId);
			if (input.expiresInDays < 1 || input.expiresInDays > 30) {
				throw new ApiError(422, 'INVALID_EXPIRY', 'Keys expire after 1 to 30 days.');
			}
			const id = randomBytes(2).toString('hex');
			const key: AgentKey = {
				jti: `k-${id}`,
				prefix: `se_ag_${id}`,
				label: input.label,
				scopes: PRESET_SCOPES[input.preset],
				createdAt: new Date().toISOString(),
				createdBy: caller.user.name,
				expiresAt: daysFromNow(input.expiresInDays),
				lastUsedAt: null,
				revokedAt: null
			};
			(s.keys[a.id] ??= []).push(key);
			append(s, {
				at: key.createdAt,
				organisationId: a.organisationId,
				actor: userActor(caller),
				type: 'AGENT_TOKEN_ISSUED',
				subjectId: a.id,
				summary: `${caller.user.name} issued the Agent token "${key.label}" to ${a.name}, ${input.preset === 'PURCHASING' ? 'purchasing' : 'research only'}, for ${input.expiresInDays} days`,
				payload: { label: key.label, preset: input.preset, scopes: key.scopes }
			});
			return { key, secret: `${key.prefix}_${randomBytes(24).toString('base64url')}` };
		},
		async revokeKey(caller, agentId, jti) {
			const s = store();
			const a = findAgent(s, caller, agentId);
			const key = s.keys[a.id]?.find((k) => k.jti === jti);
			if (!key) throw new ApiError(404, 'NOT_FOUND', 'No such key.');
			if (!key.revokedAt) {
				key.revokedAt = new Date().toISOString();
				append(s, {
					at: key.revokedAt,
					organisationId: a.organisationId,
					actor: userActor(caller),
					type: 'AGENT_TOKEN_REVOKED',
					subjectId: a.id,
					summary: `${caller.user.name} revoked the Agent token "${key.label}" of ${a.name}; it is refused from the next request`,
					payload: { label: key.label }
				});
			}
			return key;
		}
	},

	audit: {
		async list(caller, filter, page = {}) {
			const limit = page.limit ?? 50;
			const matching = newestFirst(visible(caller, store().audit)).filter(
				(e) =>
					(!filter.agentId || agentOf(e) === filter.agentId) &&
					(!filter.type || e.type === filter.type) &&
					(!filter.subject || e.subjectId === filter.subject) &&
					(!filter.from || e.at >= filter.from) &&
					(!filter.to || e.at < filter.to)
			);
			// The cursor is the last event read, as in the backend, so events recorded since
			// (which sort first) don't shift the next page.
			const after = page.cursor ? matching.findIndex((e) => e.id === page.cursor) : -1;
			// An unknown cursor reads nothing rather than starting over.
			const start = page.cursor && after < 0 ? matching.length : after + 1;
			const items = matching.slice(start, start + limit);
			const more = start + limit < matching.length;
			return {
				items: items.map(toAuditEvent),
				nextCursor: more ? items.at(-1)!.id : null
			};
		},
		async orderTrail(caller, orderId) {
			const s = store();
			const o = visible(caller, s.orders).find((x) => x.orderId === orderId);
			if (!o) return null;
			// The order and its quote; the agent's substitute requests up to the quote. The mock
			// has no revised quotes, so there's no earlier quote to follow.
			const quoted = s.audit.find((e) => e.subjectId === o.quoteId)?.at ?? o.createdAt;
			const asked = new Set(o.lines.flatMap((l) => l.substitutesFor ?? []));
			return s.audit
				.filter(
					(e) =>
						e.subjectId === o.orderId ||
						e.subjectId === o.quoteId ||
						(e.type === 'SUBSTITUTES_REQUESTED' &&
							e.actor.id === o.agent.id &&
							e.at <= quoted &&
							asked.has(String(e.payload.productCode)))
				)
				.toSorted((a, b) => a.at.localeCompare(b.at))
				.map(toAuditEvent);
		}
	},

	oversight: {
		async feed(caller) {
			requireStaff(caller);
			return newestFirst(store().audit).slice(0, 80);
		},
		async scenarios(caller) {
			requireStaff(caller);
			return store().scenarios;
		},
		async setScenario(caller, id, active) {
			requireStaff(caller);
			const sc = store().scenarios.find((x) => x.id === id);
			if (!sc) throw new ApiError(404, 'NOT_FOUND', 'No such scenario.');
			sc.active = active;
			return sc;
		},
		async addScenario(caller, input) {
			requireStaff(caller);
			const sc: ScenarioOverride = {
				id: `sc-${randomBytes(3).toString('hex')}`,
				productCode: input.productCode,
				productName: `Product ${input.productCode}`,
				kind: input.kind,
				detail: input.detail,
				active: true
			};
			store().scenarios.push(sc);
			return sc;
		},
		async simulateAgentOrder(caller, organisationId) {
			requireStaff(caller);
			const s = store();
			const template = buildOrders().find(
				(o) => o.organisationId === organisationId && o.status === 'PENDING_APPROVAL'
			);
			if (!template)
				throw new ApiError(404, 'NOT_FOUND', 'No order template for that organisation.');
			const now = new Date().toISOString();
			const order: MockOrder = {
				...template,
				orderId: randomUUID(),
				quoteId: randomUUID(),
				createdAt: now,
				statusHistory: [{ status: 'PENDING_APPROVAL', at: now, by: `agent:${template.agent.name}` }]
			};
			s.orders.push(order);
			seedOrderTrail(s, order);
			return { orderId: order.orderId, organisationName: orgName(organisationId) };
		}
	}
};
