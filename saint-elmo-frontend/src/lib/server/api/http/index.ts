import type {
	AgentKey,
	AgentSummary,
	AuditEvent,
	BackendMe,
	IssuedKey,
	Order,
	ProductDetail,
	ProductSearchResponse,
	ScenarioOverride,
	SessionUser,
	Vocabulary
} from '#lib/api/types.js';
import { ApiError, type Caller, type SaintElmoApi } from '../client';

type CallInit = Omit<RequestInit, 'body'> & {
	caller?: Caller;
	/** A bearer token without a resolved user yet, e.g. right after sign-in. */
	token?: string;
	query?: Record<string, string | undefined>;
	/** Sent as JSON. */
	json?: unknown;
	/** Sent as application/x-www-form-urlencoded, as OAuth 2.0 expects. */
	form?: Record<string, string>;
};

/** The backend's session user, in the shape the pages use. */
function sessionUser(me: BackendMe): SessionUser {
	return {
		id: me.publicId,
		name: `${me.firstName} ${me.lastName}`.trim(),
		email: me.email,
		role: me.role,
		organisation: { id: me.organization.publicId, name: me.organization.name }
	};
}

/**
 * The FastAPI implementation. Sign-in and the catalog call routes that exist today;
 * orders, agents, audit and scenario controls follow issues #15 and #22 and are marked
 * TODO until those land. Switch a namespace over with API_MODE_<NAMESPACE>=http.
 */
export function httpApi(baseUrl: string): SaintElmoApi {
	async function call<T>(path: string, init: CallInit = {}): Promise<T> {
		const { caller, token, query, json, form, ...rest } = init;
		const url = new URL(path, baseUrl);
		for (const [k, v] of Object.entries(query ?? {})) if (v) url.searchParams.set(k, v);
		const headers = new Headers(rest.headers);
		headers.set('accept', 'application/json');
		let body: BodyInit | undefined;
		if (json !== undefined) {
			headers.set('content-type', 'application/json');
			body = JSON.stringify(json);
		} else if (form) {
			body = new URLSearchParams(form);
		}
		const bearer = caller?.token ?? token;
		if (bearer) headers.set('authorization', `Bearer ${bearer}`);

		let res: Response;
		try {
			res = await fetch(url, { ...rest, headers, body });
		} catch {
			throw new ApiError(
				503,
				'BACKEND_UNREACHABLE',
				`Saint Elmo’s backend at ${url.origin} isn’t answering. Is it running?`
			);
		}
		if (res.status === 204) return undefined as T;
		const payload = await res.json().catch(() => null);
		if (!res.ok) {
			// The backend's error envelope: { error: { code, message, requestId } } (api/error_handlers.py)
			const err = payload?.error ?? {};
			throw new ApiError(
				res.status,
				err.code ?? `HTTP_${res.status}`,
				err.message ?? `The backend answered ${res.status} for ${url.pathname}.`
			);
		}
		return payload as T;
	}

	const orNull = async <T>(p: Promise<T>) => {
		try {
			return await p;
		} catch (e) {
			if (e instanceof ApiError && e.status === 404) return null;
			throw e;
		}
	};

	return {
		auth: {
			async login(email, password) {
				const grant = await call<{ access_token: string; expires_in: number }>(
					'/api/v1/auth/token',
					{ method: 'POST', form: { grant_type: 'password', username: email, password } }
				);
				const me = await call<BackendMe>('/api/v1/auth/me', { token: grant.access_token });
				return {
					token: grant.access_token,
					user: sessionUser(me),
					expiresInSeconds: grant.expires_in
				};
			},
			async session(token) {
				try {
					return sessionUser(await call<BackendMe>('/api/v1/auth/me', { token }));
				} catch (e) {
					if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return null;
					throw e;
				}
			},
			demoAccounts: async () => []
		},

		catalog: {
			search: (caller, request) =>
				call<ProductSearchResponse>('/api/v1/products/search', {
					caller,
					method: 'POST',
					json: request
				}),
			product: (caller, code) =>
				orNull(
					call<ProductDetail>(`/api/v1/products/${encodeURIComponent(code)}`, {
						caller,
						query: { language: 'en' }
					})
				),
			vocabulary: (caller) => call<Vocabulary>('/api/v1/catalog/vocabulary', { caller })
		},

		// TODO(#15): confirm paths once the orders and approval API lands.
		orders: {
			async list(caller, filter) {
				const page = await call<{ items: Order[] }>('/api/v1/orders', {
					caller,
					query: { status: filter?.status }
				});
				return page.items;
			},
			get: (caller, orderId) =>
				orNull(call<Order>(`/api/v1/orders/${encodeURIComponent(orderId)}`, { caller })),
			approve: (caller, orderId, note) =>
				call(`/api/v1/orders/${encodeURIComponent(orderId)}/approve`, {
					caller,
					method: 'POST',
					json: { note }
				}),
			reject: (caller, orderId, note) =>
				call(`/api/v1/orders/${encodeURIComponent(orderId)}/reject`, {
					caller,
					method: 'POST',
					json: { note }
				})
		},

		// TODO(#22): confirm paths once the agent token management API lands.
		agents: {
			list: (caller) => call<AgentSummary[]>('/api/v1/agents', { caller }),
			get: (caller, agentId) =>
				orNull(call<AgentSummary>(`/api/v1/agents/${encodeURIComponent(agentId)}`, { caller })),
			create: (caller, input) => call('/api/v1/agents', { caller, method: 'POST', json: input }),
			setStatus: (caller, agentId, status) =>
				call(`/api/v1/agents/${encodeURIComponent(agentId)}`, {
					caller,
					method: 'PATCH',
					json: { status }
				}),
			listKeys: (caller, agentId) =>
				call<AgentKey[]>(`/api/v1/agents/${encodeURIComponent(agentId)}/tokens`, { caller }),
			issueKey: (caller, agentId, input) =>
				call<IssuedKey>(`/api/v1/agents/${encodeURIComponent(agentId)}/tokens`, {
					caller,
					method: 'POST',
					json: input
				}),
			revokeKey: (caller, agentId, jti) =>
				call<AgentKey>(
					`/api/v1/agents/${encodeURIComponent(agentId)}/tokens/${encodeURIComponent(jti)}/revoke`,
					{ caller, method: 'POST' }
				)
		},

		// TODO: audit endpoint is not specified in an issue yet.
		audit: {
			list: (caller, filter) =>
				call<AuditEvent[]>('/api/v1/audit', {
					caller,
					query: {
						agentId: filter.agentId,
						orderId: filter.orderId,
						type: filter.type,
						outcome: filter.outcome
					}
				})
		},

		// TODO: scenario controls (design §3.3) have no issue yet.
		oversight: {
			feed: (caller) => call<AuditEvent[]>('/api/v1/oversight/feed', { caller }),
			scenarios: (caller) => call<ScenarioOverride[]>('/api/v1/scenarios', { caller }),
			setScenario: (caller, id, active) =>
				call(`/api/v1/scenarios/${encodeURIComponent(id)}`, {
					caller,
					method: 'PATCH',
					json: { active }
				}),
			addScenario: (caller, input) =>
				call('/api/v1/scenarios', { caller, method: 'POST', json: input }),
			async simulateAgentOrder() {
				throw new ApiError(
					501,
					'NOT_AVAILABLE',
					'Simulated orders exist only in mock mode. Use a real agent through MCP instead.'
				);
			}
		}
	};
}
