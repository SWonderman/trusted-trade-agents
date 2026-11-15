import type {
	AgentKey,
	AgentStatus,
	AgentSummary,
	Claim,
	Iso,
	KeyPreset,
	Mandate,
	Money,
	PeriodSpend
} from '#lib/api/types.js';
import { isUuid } from '#lib/ids.js';
import { ApiError, type AgentsApi, type Caller } from '../client';

/** The http client's call, as much of it as the agents area needs. */
export type Call = <T>(
	path: string,
	init: { caller: Caller; method?: string; json?: unknown }
) => Promise<T>;

// --- The backend's shapes (saint_elmo_backend/agents/schemas.py, mandates/schemas.py) ---

interface BackendAgent {
	id: string;
	name: string;
	status: AgentStatus;
}

interface BackendMandate extends Omit<Mandate, 'maxSubstitutePriceIncreasePct'> {
	maxSubstitutePriceIncreasePct: number;
	periodSpend: PeriodSpend;
}

/** GET /api/v1/agents/{agentId} */
interface BackendAgentDetail extends BackendAgent {
	mandate: BackendMandate | null;
	liveTokens: number;
	lastUsedAt: Iso | null;
}

/** GET /api/v1/agents/{agentId}/tokens, one item */
interface BackendToken {
	jti: string;
	label: string;
	scopes: string[];
	expiresAt: Iso;
	createdAt: Iso;
	createdBy: { id: string; name: string };
	lastUsedAt: Iso | null;
	revokedAt: Iso | null;
}

/** The backend's names for the console's presets (ScopePreset). */
const PRESET: Record<KeyPreset, string> = {
	PURCHASING: 'Purchasing',
	RESEARCH_ONLY: 'Research only'
};

const NO_MANDATE: Mandate = {
	version: 0,
	maxOrderTotal: 0,
	autoApproveUpTo: 0,
	periodSpendCap: 0,
	spendPeriod: 'WEEK',
	categorySpendCaps: [],
	allowedCategoryCodes: [],
	blockedCategoryCodes: [],
	allowedVendors: [],
	blockedVendors: [],
	allowedCountriesOfOrigin: [],
	requiredClaims: [],
	requiredLabels: [],
	requiredDiets: [],
	excludedAllergens: [],
	allergenStrictness: 'contains',
	substitutionPolicy: 'NEVER',
	maxSubstitutePriceIncreasePct: null,
	laterDeliveryNeedsApproval: true,
	minDeliveryReliability: null
};

/** Only the console's mandate fields, leaving out the backend's agent and organisation echo. */
function mandateOf(m: BackendMandate): Mandate {
	return {
		version: m.version,
		maxOrderTotal: m.maxOrderTotal,
		autoApproveUpTo: m.autoApproveUpTo,
		periodSpendCap: m.periodSpendCap,
		spendPeriod: m.spendPeriod,
		allowedCategoryCodes: m.allowedCategoryCodes,
		blockedCategoryCodes: m.blockedCategoryCodes,
		allowedVendors: m.allowedVendors,
		blockedVendors: m.blockedVendors,
		allowedCountriesOfOrigin: m.allowedCountriesOfOrigin,
		requiredLabels: m.requiredLabels,
		requiredDiets: m.requiredDiets,
		excludedAllergens: m.excludedAllergens,
		allergenStrictness: m.allergenStrictness,
		substitutionPolicy: m.substitutionPolicy,
		maxSubstitutePriceIncreasePct: m.maxSubstitutePriceIncreasePct,
		laterDeliveryNeedsApproval: m.laterDeliveryNeedsApproval,
		minDeliveryReliability: m.minDeliveryReliability,
		categorySpendCaps: m.categorySpendCaps.map((c) => ({
			categoryCode: c.categoryCode,
			cap: c.cap
		})),
		requiredClaims: m.requiredClaims.map((c: Claim) => ({ type: c.type, element: c.element }))
	};
}

function summaryOf(a: BackendAgentDetail): AgentSummary {
	const now = new Date().toISOString();
	const spend: PeriodSpend = a.mandate?.periodSpend ?? {
		periodStart: now,
		periodEnd: now,
		committed: 0 as Money,
		remaining: 0 as Money
	};
	return {
		id: a.id,
		name: a.name,
		// The backend keeps no purpose for an agent.
		purpose: '',
		status: a.status,
		// An agent without a mandate can't get a token, so it shows as allowed nothing.
		mandate: a.mandate ? mandateOf(a.mandate) : NO_MANDATE,
		periodSpend: {
			periodStart: spend.periodStart,
			periodEnd: spend.periodEnd,
			committed: spend.committed,
			remaining: spend.remaining
		},
		activeKeys: a.liveTokens,
		lastActiveAt: a.lastUsedAt
	};
}

function keyOf(t: BackendToken): AgentKey {
	return {
		jti: t.jti,
		// Token values are never stored, so keys are told apart by the start of their id.
		prefix: t.jti.slice(0, 8),
		label: t.label,
		scopes: t.scopes,
		createdAt: t.createdAt,
		createdBy: t.createdBy.name,
		expiresAt: t.expiresAt,
		lastUsedAt: t.lastUsedAt,
		revokedAt: t.revokedAt
	};
}

const notAvailable = (what: string) =>
	new ApiError(501, 'NOT_AVAILABLE', `${what} isn’t available on Saint Elmo’s backend yet.`);

/** The buyer admin's agent routes under /api/v1/agents, as they are. */
export function httpAgents(call: Call): AgentsApi {
	const agentPath = (agentId: string) => `/api/v1/agents/${encodeURIComponent(agentId)}`;

	async function get(caller: Caller, agentId: string): Promise<AgentSummary | null> {
		// Agent ids are UUIDs; the backend refuses anything else with a 422, not a 404.
		if (!isUuid(agentId)) return null;
		try {
			return summaryOf(await call<BackendAgentDetail>(agentPath(agentId), { caller }));
		} catch (e) {
			if (e instanceof ApiError && e.status === 404) return null;
			throw e;
		}
	}

	async function listKeys(caller: Caller, agentId: string): Promise<AgentKey[]> {
		const { items } = await call<{ items: BackendToken[] }>(`${agentPath(agentId)}/tokens`, {
			caller
		});
		return items.map(keyOf);
	}

	return {
		async list(caller) {
			const { items } = await call<{ items: BackendAgent[] }>('/api/v1/agents', { caller });
			const agents = await Promise.all(items.map((a) => get(caller, a.id)));
			return agents.filter((a): a is AgentSummary => a !== null);
		},

		get,

		async create() {
			throw notAvailable('Creating an agent');
		},

		async setStatus(caller, agentId, status) {
			// The backend can disable an agent but not enable it again.
			if (status === 'ACTIVE') throw notAvailable('Enabling a disabled agent');
			await call(`${agentPath(agentId)}/disable`, { caller, method: 'POST' });
			const agent = await get(caller, agentId);
			if (!agent) throw new ApiError(404, 'AGENT_NOT_FOUND', 'There’s no such agent.');
			return agent;
		},

		listKeys,

		async issueKey(caller, agentId, input) {
			const issued = await call<{ token: string; jti: string }>(`${agentPath(agentId)}/tokens`, {
				caller,
				method: 'POST',
				json: {
					label: input.label,
					preset: PRESET[input.preset],
					expiresInDays: input.expiresInDays
				}
			});
			// The list has what the issue answer leaves out, such as who issued it and when.
			const key = (await listKeys(caller, agentId)).find((k) => k.jti === issued.jti);
			if (!key) throw new ApiError(502, 'KEY_NOT_LISTED', 'The new key isn’t in the agent’s list.');
			return { key, secret: issued.token };
		},

		async revokeKey(caller, agentId, jti) {
			return keyOf(
				await call<BackendToken>(`${agentPath(agentId)}/tokens/${encodeURIComponent(jti)}`, {
					caller,
					method: 'DELETE'
				})
			);
		}
	};
}
