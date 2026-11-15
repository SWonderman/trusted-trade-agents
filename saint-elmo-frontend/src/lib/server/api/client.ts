import type {
	AgentKey,
	AgentSummary,
	AuditEvent,
	AuditFilter,
	IssuedKey,
	KeyPreset,
	NewAgentInput,
	Order,
	OrderStatus,
	ProductDetail,
	ProductSearchRequest,
	ProductSearchResponse,
	ScenarioKind,
	ScenarioOverride,
	SessionUser,
	Vocabulary
} from '#lib/api/types.js';

/**
 * Everything the frontend needs from the backend, grouped the way the FastAPI
 * routes are. Two implementations exist: `mock/` (in memory) and `http/`
 * (FastAPI). Load functions and form actions only ever see this interface.
 */
export interface SaintElmoApi {
	auth: AuthApi;
	catalog: CatalogApi;
	orders: OrdersApi;
	agents: AgentsApi;
	audit: AuditApi;
	oversight: OversightApi;
}

/** Who is calling. The http implementation turns this into a bearer token. */
export interface Caller {
	token: string;
	user: SessionUser;
}

export interface AuthApi {
	/** POST /api/v1/auth/token (OAuth 2.0 password grant), then GET /api/v1/auth/me. */
	login(
		email: string,
		password: string
	): Promise<{ token: string; user: SessionUser; expiresInSeconds: number }>;
	/** Resolves a token to its user, or null if it is unknown or expired. */
	session(token: string): Promise<SessionUser | null>;
	/** Seeded accounts to show on the login page in demo mode; empty when live. */
	demoAccounts(): Promise<{ email: string; password: string; label: string }[]>;
}

/**
 * The catalog, read-only, as a reference for writing mandates. Live offers stay
 * agent-only: people manage agents here, agents do the buying.
 */
export interface CatalogApi {
	/** POST /api/v1/products/search */
	search(caller: Caller, request: ProductSearchRequest): Promise<ProductSearchResponse>;
	/** GET /api/v1/products/{code}, or null when there is no such product. */
	product(caller: Caller, code: string): Promise<ProductDetail | null>;
	/** GET /api/v1/catalog/vocabulary: the filter codes products actually use. */
	vocabulary(caller: Caller): Promise<Vocabulary>;
}

export interface OrdersApi {
	/** GET /api/v1/orders?status=: most recent first; every order in that status, or the 100 most recent. */
	list(caller: Caller, filter?: { status?: OrderStatus }): Promise<Order[]>;
	/** GET /api/v1/orders/{orderId}, or null when the caller's organisation has no such order. */
	get(caller: Caller, orderId: string): Promise<Order | null>;
	/**
	 * POST /api/v1/orders/{orderId}/approve (people only). Re-checks live data first, so
	 * the order comes back PLACED, REJECTED by a hard rule that now applies, or still
	 * PENDING_APPROVAL with reasons or a total the approver hasn't seen.
	 */
	approve(caller: Caller, orderId: string, note?: string): Promise<Order>;
	/** POST /api/v1/orders/{orderId}/reject (people only) */
	reject(caller: Caller, orderId: string, note?: string): Promise<Order>;
}

export interface AgentsApi {
	list(caller: Caller): Promise<AgentSummary[]>;
	get(caller: Caller, agentId: string): Promise<AgentSummary | null>;
	create(caller: Caller, input: NewAgentInput): Promise<AgentSummary>;
	setStatus(caller: Caller, agentId: string, status: 'ACTIVE' | 'DISABLED'): Promise<AgentSummary>;
	listKeys(caller: Caller, agentId: string): Promise<AgentKey[]>;
	issueKey(
		caller: Caller,
		agentId: string,
		input: { label: string; preset: KeyPreset; expiresInDays: number }
	): Promise<IssuedKey>;
	revokeKey(caller: Caller, agentId: string, jti: string): Promise<AgentKey>;
}

export interface AuditApi {
	list(caller: Caller, filter: AuditFilter): Promise<AuditEvent[]>;
}

export interface OversightApi {
	/** Cross-customer feed, Valio Aimo staff only. */
	feed(caller: Caller): Promise<AuditEvent[]>;
	scenarios(caller: Caller): Promise<ScenarioOverride[]>;
	setScenario(caller: Caller, id: string, active: boolean): Promise<ScenarioOverride>;
	addScenario(
		caller: Caller,
		input: { productCode: string; kind: ScenarioKind; detail: string }
	): Promise<ScenarioOverride>;
	/** Demo only: inject an order as if an agent had placed it through MCP. */
	simulateAgentOrder(
		caller: Caller,
		organisationId: string
	): Promise<{ orderId: string; organisationName: string }>;
}

/** A failure the UI can explain. `code` follows the backend's error codes. */
export class ApiError extends Error {
	constructor(
		readonly status: number,
		readonly code: string,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}
