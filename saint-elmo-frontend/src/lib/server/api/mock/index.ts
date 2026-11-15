import { createHash, randomBytes, randomUUID } from 'node:crypto';
import type {
	AgentKey,
	AgentSummary,
	AuditEvent,
	KeyPreset,
	Mandate,
	Order,
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
	audit: AuditEvent[];
	scenarios: ScenarioOverride[];
	seq: number;
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

// --- Audit trail with a hash chain ------------------------------------------

function hashOf(prev: string, body: object) {
	return createHash('sha256')
		.update(prev + JSON.stringify(body))
		.digest('hex')
		.slice(0, 16);
}

function append(s: Store, event: Omit<AuditEvent, 'id' | 'prevHash' | 'hash'>) {
	const prevHash = s.audit.at(-1)?.hash ?? '0'.repeat(16);
	const id = `EV-${String(++s.seq).padStart(5, '0')}`;
	const hash = hashOf(prevHash, { id, ...event });
	s.audit.push({ id, prevHash, hash, ...event });
}

function orgName(id: string) {
	return ORGS.find((o) => o.id === id)?.name ?? id;
}

function seedOrderTrail(s: Store, o: MockOrder) {
	const t0 = new Date(o.createdAt).getTime();
	const at = (minBefore: number) => new Date(t0 - minBefore * 60_000).toISOString();
	const base = {
		organisationId: o.organisationId,
		organisationName: orgName(o.organisationId),
		actor: { kind: 'agent' as const, name: o.agent.name },
		agentId: o.agent.id
	};
	const sub = o.lines.find((l) => l.substitutesFor);

	append(s, {
		...base,
		at: at(4),
		type: 'TOOL_CALL',
		tool: 'search_products',
		summary: `Searched the catalog for “${(o.lines[0].name ?? o.lines[0].productCode).split(' ').slice(0, 3).join(' ')}…”`
	});
	append(s, {
		...base,
		at: at(3),
		type: 'TOOL_CALL',
		tool: 'get_offers',
		summary: `Fetched live price and availability for ${o.lines.length + 3} products`
	});
	if (sub) {
		append(s, {
			...base,
			at: at(2),
			type: 'TOOL_CALL',
			tool: 'find_substitutes',
			summary: `Asked for substitutes for ${sub.substitutesFor}`
		});
	}
	append(s, {
		...base,
		at: at(1),
		type: 'QUOTE_CREATED',
		tool: 'create_quote',
		quoteId: o.quoteId,
		summary: `Quote ${shortId(o.quoteId)} for €${o.totals.net.toLocaleString('en-GB')}, judged against mandate v${o.policy.mandateVersion}`,
		outcome: o.policy.outcome,
		reasonCodes: o.policy.reasons.map((r) => r.code)
	});
	append(s, {
		...base,
		at: o.createdAt,
		type: 'ORDER_REQUESTED',
		tool: 'place_order',
		quoteId: o.quoteId,
		orderId: o.orderId,
		summary: `Placed order from quote ${shortId(o.quoteId)}; live price and availability re-checked`,
		outcome: o.policy.outcome,
		reasonCodes: o.policy.reasons.map((r) => r.code),
		stateChange: { from: null, to: o.statusHistory[0].status }
	});
	for (const [i, h] of o.statusHistory.slice(1).entries()) {
		append(s, {
			...base,
			actor: { kind: 'system', name: 'policy' },
			at: h.at,
			type: `ORDER_${h.status}`,
			orderId: o.orderId,
			summary: `Order moved to ${h.status.toLowerCase().replace('_', ' ')}`,
			stateChange: { from: o.statusHistory[i].status, to: h.status }
		});
	}
}

function seed(): Store {
	const s: Store = {
		orders: buildOrders(),
		agents: AGENTS.map((a) => ({ ...a, mandate: structuredClone(MANDATES[a.id]) })),
		keys: structuredClone(KEYS),
		audit: [],
		scenarios: structuredClone(SCENARIOS),
		seq: 0
	};
	append(s, {
		at: minutesAgo(60 * 24 * 3),
		organisationId: 'org-aurora',
		organisationName: orgName('org-aurora'),
		actor: { kind: 'user', name: 'Helmi Virtanen' },
		type: 'KEY_ISSUED',
		agentId: 'agt-dairy',
		summary: 'Issued key se_ag_7f2a (Purchasing, 7 days) to dairy-restock'
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
	const base = {
		organisationId: before.organisationId,
		organisationName: orgName(before.organisationId),
		actor: { kind: 'user' as const, name: caller.user.name },
		agentId: before.agent.id,
		orderId: before.orderId
	};
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
			actor: { kind: 'system', name: 'policy' },
			at: now,
			type: 'ORDER_RECHECKED',
			summary: `Re-checked live data on approval: ${checked.policy.outcome}`,
			outcome: checked.policy.outcome,
			reasonCodes: checked.policy.reasons.map((r) => r.code)
		});
		if (checked.policy.outcome === 'REJECT') {
			o = decided(checked, { status: 'REJECTED', at: now, by });
			append(s, {
				...base,
				actor: { kind: 'system', name: 'policy' },
				at: now,
				type: 'ORDER_REJECTED',
				summary: 'The re-check on approval found a hard rule broken; the order is rejected',
				outcome: 'REJECT',
				reasonCodes: checked.policy.reasons
					.filter((r) => r.severity === 'REJECT')
					.map((r) => r.code),
				stateChange: { from: 'PENDING_APPROVAL', to: 'REJECTED' }
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
				summary: note ? `Approved: “${note}”` : 'Approved without a note',
				stateChange: { from: 'PENDING_APPROVAL', to: 'APPROVED' }
			});
			append(s, {
				...base,
				actor: { kind: 'system', name: 'order book' },
				at: now,
				type: 'ORDER_PLACED',
				summary: 'Live re-check passed; recorded in the order book',
				stateChange: { from: 'APPROVED', to: 'PLACED' }
			});
		}
	} else {
		o = decided(before, { status: 'REJECTED', at: now, by });
		append(s, {
			...base,
			at: now,
			type: 'ORDER_REJECTED_BY_HUMAN',
			summary: note ? `Rejected: “${note}”` : 'Rejected without a note',
			stateChange: { from: 'PENDING_APPROVAL', to: 'REJECTED' }
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
			append(s, {
				at: new Date().toISOString(),
				organisationId: org.id,
				organisationName: org.name,
				actor: { kind: 'user', name: caller.user.name },
				type: 'AGENT_CREATED',
				agentId: row.id,
				summary: `Created agent ${row.name} with mandate v1`
			});
			return summary(s, row);
		},
		async setStatus(caller, agentId, status) {
			const s = store();
			const a = findAgent(s, caller, agentId);
			a.status = status;
			append(s, {
				at: new Date().toISOString(),
				organisationId: a.organisationId,
				organisationName: orgName(a.organisationId),
				actor: { kind: 'user', name: caller.user.name },
				type: status === 'DISABLED' ? 'AGENT_DISABLED' : 'AGENT_ENABLED',
				agentId: a.id,
				summary: `${status === 'DISABLED' ? 'Disabled' : 'Enabled'} ${a.name}; ${status === 'DISABLED' ? 'all its keys are refused' : 'its unrevoked keys work again'}`
			});
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
				organisationName: orgName(a.organisationId),
				actor: { kind: 'user', name: caller.user.name },
				type: 'KEY_ISSUED',
				agentId: a.id,
				summary: `Issued key ${key.prefix} (${input.preset === 'PURCHASING' ? 'Purchasing' : 'Research only'}, ${input.expiresInDays} days) to ${a.name}`
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
					organisationName: orgName(a.organisationId),
					actor: { kind: 'user', name: caller.user.name },
					type: 'KEY_REVOKED',
					agentId: a.id,
					summary: `Revoked key ${key.prefix} of ${a.name}; refused from the next request`
				});
			}
			return key;
		}
	},

	audit: {
		async list(caller, filter) {
			// An order filter also matches its quote, so the trail shows how the order came about.
			const quoteId = filter.orderId
				? (store().orders.find((o) => o.orderId === filter.orderId)?.quoteId ?? filter.orderId)
				: undefined;
			return visible(caller, store().audit)
				.filter(
					(e) =>
						(!filter.agentId || e.agentId === filter.agentId) &&
						(!filter.orderId || e.orderId === filter.orderId || e.quoteId === quoteId) &&
						(!filter.type || e.type === filter.type || e.tool === filter.type) &&
						(!filter.outcome || e.outcome === filter.outcome)
				)
				.toReversed();
		}
	},

	oversight: {
		async feed(caller) {
			requireStaff(caller);
			return store().audit.toReversed().slice(0, 80);
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
