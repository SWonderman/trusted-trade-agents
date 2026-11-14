import { createHash, randomBytes } from 'node:crypto';
import type {
	AgentKey,
	AgentSummary,
	AuditEvent,
	KeyPreset,
	Mandate,
	Order,
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
	minutesAgo
} from './fixtures';

/**
 * In-memory stand-in for the FastAPI backend. State lives on globalThis so it
 * survives Vite hot reloads; it resets when the dev server restarts.
 *
 * Tenant isolation is mirrored here the way Postgres RLS will enforce it:
 * every read and write is filtered by the caller's organisation.
 */

type AgentRow = (typeof AGENTS)[number] & { mandate: Mandate };

interface Store {
	orders: Order[];
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

function seedOrderTrail(s: Store, o: Order) {
	const t0 = new Date(o.createdAt).getTime();
	const at = (minBefore: number) => new Date(t0 - minBefore * 60_000).toISOString();
	const base = {
		organisationId: o.organisationId,
		organisationName: o.organisationName,
		actor: { kind: 'agent' as const, name: o.agent.name },
		agentId: o.agent.id
	};
	const sub = o.lines.find((l) => l.substitutesFor);

	append(s, {
		...base,
		at: at(4),
		type: 'TOOL_CALL',
		tool: 'search_products',
		summary: `Searched the catalog for “${o.lines[0].product.name.split(' ').slice(0, 3).join(' ')}…”`
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
			summary: `Asked for substitutes for ${sub.substitutesFor!.code}`
		});
	}
	append(s, {
		...base,
		at: at(1),
		type: 'QUOTE_CREATED',
		tool: 'create_quote',
		quoteId: o.quoteId,
		summary: `Quote ${o.quoteId} for €${o.totals.net.toLocaleString('en-GB')}, judged against mandate v${o.policy.mandateVersion}`,
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
		summary: `Placed order from ${o.quoteId}; live price and availability re-checked`,
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
		organisationId: 'org-kajo',
		organisationName: orgName('org-kajo'),
		actor: { kind: 'user', name: 'Aino Virtanen' },
		type: 'KEY_ISSUED',
		agentId: 'agt-dairy',
		summary: 'Issued key se_ag_7f2a (Purchasing, 7 days) to dairy-restock'
	});
	const chronological = [...s.orders].sort((a, b) => a.createdAt.localeCompare(b.createdAt));
	for (const o of chronological) seedOrderTrail(s, o);
	return s;
}

// --- Helpers ----------------------------------------------------------------

function orgOf(caller: Caller) {
	return caller.user.organisation?.id ?? null;
}

function visible<T extends { organisationId: string }>(caller: Caller, rows: T[]) {
	const org = orgOf(caller);
	// Valio Aimo staff read across customers; everyone else sees only their own.
	return caller.user.role === 'aimo_staff' ? rows : rows.filter((r) => r.organisationId === org);
}

function requireBuyer(caller: Caller) {
	if (caller.user.role === 'aimo_staff' || !caller.user.organisation) {
		throw new ApiError(
			403,
			'PERMISSION_DENIED',
			'Only people in the buyer organisation can do this.'
		);
	}
	return caller.user.organisation;
}

function requireStaff(caller: Caller) {
	if (caller.user.role !== 'aimo_staff') {
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

function decide(caller: Caller, orderId: string, approve: boolean, note?: string) {
	const s = store();
	requireBuyer(caller);
	const o = visible(caller, s.orders).find((x) => x.orderId === orderId);
	if (!o) throw new ApiError(404, 'NOT_FOUND', 'No such order in your organisation.');
	if (o.status !== 'PENDING_APPROVAL') {
		throw new ApiError(
			409,
			'ORDER_NOT_PENDING',
			`This order is already ${o.status.toLowerCase()}.`
		);
	}
	const by = `user:${caller.user.name}`;
	const now = new Date().toISOString();
	const base = {
		organisationId: o.organisationId,
		organisationName: o.organisationName,
		actor: { kind: 'user' as const, name: caller.user.name },
		agentId: o.agent.id,
		orderId: o.orderId
	};

	if (approve) {
		// The backend re-checks live data on approval (#15). Closing time is the
		// check most likely to have changed since the agent placed the order.
		const late = o.lines.find((l) => new Date(l.offer.closingTime).getTime() < Date.now());
		if (late) {
			o.status = 'REJECTED';
			o.statusHistory.push({
				status: 'REJECTED',
				at: now,
				by: 'system',
				note: 'Closing time passed'
			});
			append(s, {
				...base,
				actor: { kind: 'system', name: 'policy' },
				at: now,
				type: 'ORDER_REJECTED',
				summary: `Re-check on approval failed: closing time passed for ${late.ref}`,
				outcome: 'REJECT',
				reasonCodes: ['CLOSING_TIME_PASSED'],
				stateChange: { from: 'PENDING_APPROVAL', to: 'REJECTED' }
			});
			return o;
		}
		o.status = 'PLACED';
		o.statusHistory.push(
			{ status: 'APPROVED', at: now, by, note },
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
	} else {
		o.status = 'REJECTED';
		o.statusHistory.push({ status: 'REJECTED', at: now, by, note });
		append(s, {
			...base,
			at: now,
			type: 'ORDER_REJECTED_BY_HUMAN',
			summary: note ? `Rejected: “${note}”` : 'Rejected without a note',
			stateChange: { from: 'PENDING_APPROVAL', to: 'REJECTED' }
		});
	}
	o.approverNote = note ?? null;
	o.checkAgainAfterSeconds = null;
	return o;
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
			return { token: encodeToken(user), user };
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
					u.role === 'aimo_staff' ? 'Valio Aimo operations' : `${u.organisation?.name}, buyer admin`
			}));
		}
	},

	orders: {
		async list(caller, filter) {
			return visible(caller, store().orders)
				.filter((o) => !filter?.status || o.status === filter.status)
				.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
		},
		async get(caller, orderId) {
			return visible(caller, store().orders).find((o) => o.orderId === orderId) ?? null;
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
			const n = 137 + s.orders.length; // seed has 6 orders, so the first simulated one is ORD-0143
			const now = new Date().toISOString();
			const order: Order = {
				...template,
				orderId: `ORD-${String(n).padStart(4, '0')}`,
				quoteId: `Q-${String(400 + n).padStart(4, '0')}`,
				createdAt: now,
				statusHistory: [{ status: 'PENDING_APPROVAL', at: now, by: `agent:${template.agent.name}` }]
			};
			s.orders.push(order);
			seedOrderTrail(s, order);
			return order;
		}
	}
};
