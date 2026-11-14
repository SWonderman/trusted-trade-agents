import type {
	AgentKey,
	AgentSummary,
	AuditEvent,
	IssuedKey,
	Order,
	ScenarioOverride,
	SessionUser
} from '#lib/api/types.js';
import { ApiError, type Caller, type SaintElmoApi } from '../client';

/**
 * The FastAPI implementation. Routes follow design.md and issues #11, #15 and
 * #22; the ones not built yet are marked TODO with their issue. Switch a
 * namespace over with API_MODE_<NAMESPACE>=http once its routes exist.
 */
export function httpApi(baseUrl: string): SaintElmoApi {
	async function call<T>(
		path: string,
		init: RequestInit & { caller?: Caller; query?: Record<string, string | undefined> } = {}
	): Promise<T> {
		const url = new URL(path, baseUrl);
		for (const [k, v] of Object.entries(init.query ?? {})) if (v) url.searchParams.set(k, v);
		const headers = new Headers(init.headers);
		headers.set('accept', 'application/json');
		if (init.body) headers.set('content-type', 'application/json');
		if (init.caller) headers.set('authorization', `Bearer ${init.caller.token}`);

		const res = await fetch(url, { ...init, headers });
		if (res.status === 204) return undefined as T;
		const body = await res.json().catch(() => null);
		if (!res.ok) {
			// The backend's error envelope: { error: { code, message } } (api/exceptions.py)
			const err = body?.error ?? body?.detail ?? {};
			throw new ApiError(
				res.status,
				err.code ?? `HTTP_${res.status}`,
				err.message ?? `The backend answered ${res.status} for ${url.pathname}.`
			);
		}
		return body as T;
	}

	const json = (data: unknown) => JSON.stringify(data);

	return {
		auth: {
			login: (email, password) =>
				call('/auth/login', { method: 'POST', body: json({ email, password }) }),
			async session(token) {
				try {
					return await call<SessionUser>('/auth/me', {
						caller: { token, user: null as unknown as SessionUser }
					});
				} catch (e) {
					if (e instanceof ApiError && (e.status === 401 || e.status === 403)) return null;
					throw e;
				}
			},
			demoAccounts: async () => []
		},

		orders: {
			async list(caller, filter) {
				const page = await call<{ items: Order[] }>('/api/v1/orders', {
					caller,
					query: { status: filter?.status }
				});
				return page.items;
			},
			async get(caller, orderId) {
				try {
					return await call<Order>(`/api/v1/orders/${encodeURIComponent(orderId)}`, { caller });
				} catch (e) {
					if (e instanceof ApiError && e.status === 404) return null;
					throw e;
				}
			},
			approve: (caller, orderId, note) =>
				call(`/api/v1/orders/${encodeURIComponent(orderId)}/approve`, {
					caller,
					method: 'POST',
					body: json({ note })
				}),
			reject: (caller, orderId, note) =>
				call(`/api/v1/orders/${encodeURIComponent(orderId)}/reject`, {
					caller,
					method: 'POST',
					body: json({ note })
				})
		},

		// TODO(#22): confirm paths once the agent token management API lands.
		agents: {
			list: (caller) => call<AgentSummary[]>('/api/v1/agents', { caller }),
			async get(caller, agentId) {
				try {
					return await call<AgentSummary>(`/api/v1/agents/${encodeURIComponent(agentId)}`, {
						caller
					});
				} catch (e) {
					if (e instanceof ApiError && e.status === 404) return null;
					throw e;
				}
			},
			create: (caller, input) =>
				call('/api/v1/agents', { caller, method: 'POST', body: json(input) }),
			setStatus: (caller, agentId, status) =>
				call(`/api/v1/agents/${encodeURIComponent(agentId)}`, {
					caller,
					method: 'PATCH',
					body: json({ status })
				}),
			listKeys: (caller, agentId) =>
				call<AgentKey[]>(`/api/v1/agents/${encodeURIComponent(agentId)}/tokens`, { caller }),
			issueKey: (caller, agentId, input) =>
				call<IssuedKey>(`/api/v1/agents/${encodeURIComponent(agentId)}/tokens`, {
					caller,
					method: 'POST',
					body: json(input)
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
					body: json({ active })
				}),
			addScenario: (caller, input) =>
				call('/api/v1/scenarios', { caller, method: 'POST', body: json(input) }),
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
