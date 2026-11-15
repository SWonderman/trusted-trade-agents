/**
 * Shapes shared by the server and the pages.
 *
 * Routes the backend already serves to people (sign-in, catalog, orders, audit) use
 * types generated from its OpenAPI schema into `backend.d.ts` (`npm run gen:api`);
 * they are re-exported below under short names. The rest mirror the contracts in
 * GitHub issues #11 (mandate) and #22 (agent keys) until those routes land, then move
 * to generated types too.
 */

import type { components } from './backend';

type Schemas = components['schemas'];

// --- Generated from the backend --------------------------------------------

export type BackendMe = Schemas['MeOutput'];
export type ProductSearchRequest = Partial<Schemas['ProductSearchRequest']>;
export type ProductSearchResponse = Schemas['ProductSearchResponse'];
export type ProductHit = Schemas['ProductHit'];
export type ProductDetail = Schemas['ProductDetailResponse'];
export type Vocabulary = Schemas['VocabularyResponse'];
/** What an order's lines show about a product beyond what the order carries. */
export type ProductFacts = Pick<ProductDetail, 'name' | 'vendor' | 'claims' | 'diets' | 'labels'>;

// The audit trail (#57)
/** One decision or commitment; lookups such as searches and price checks are not recorded. */
export type AuditEvent = Schemas['AuditEventOut'];
export type AuditEventType = Schemas['AuditEventType'];
/** "system" is credited with automatic steps, e.g. placing a confirmed or approved order. */
export type ActorKind = AuditEvent['actor']['kind'];
/** A page of events, newest first; `nextCursor` reads the next, older page. */
export type AuditEventPage = Schemas['AuditEventListResponse'];
export type OrderTrail = Schemas['OrderTrailResponse'];

// Orders (#15) and the policy's judgement of them (#13)
export type Order = Schemas['OrderResponse'];
export type OrderList = Schemas['OrderListResponse'];
export type OrderStatus = Schemas['OrderStatus'];
/** A quoted line: its live offer at the latest re-check, and the policy's judgement. */
export type OrderLine = Schemas['JudgedLineOut'];
export type OrderChange = Schemas['OrderChange'];
export type StatusChange = Schemas['StatusChangeOut'];
export type Measure = Schemas['Measure'];
export type PolicyOutcome = Schemas['PolicyOutcome'];
export type PolicyReason = Schemas['PolicyReasonOut'];
export type PolicyReasonCode = Schemas['PolicyReasonCode'];
export type OfferReasonCode = Schemas['OfferReasonCode'];

export type Iso = string;
export type Money = number; // EUR, excluding VAT

// --- Principals -------------------------------------------------------------

/** The backend's roles, plus Valio Aimo staff, which only the mock has so far. */
export type Role = BackendMe['role'] | 'AIMO_STAFF';

export interface BuyerOrganisation {
	id: string;
	name: string;
	kind: 'hotel_chain' | 'hospital' | 'school';
	customerNumber: string;
}

export interface SessionUser {
	id: string;
	name: string;
	email: string;
	role: Role;
	/** null for Valio Aimo staff, who belong to no buyer organisation */
	organisation: Pick<BuyerOrganisation, 'id' | 'name'> | null;
}

// --- Catalog (mock fixtures) ---------------------------------------------------

export interface Claim {
	type: string; // GS1 claim type, e.g. FREE_FROM
	element: string; // e.g. LACTOSE
}

export interface CarbonFootprint {
	value: number; // kg CO2-eq per kg
	basis: 'PRODUCT_GROUP_AVERAGE';
}

export interface ProductRef {
	code: string;
	name: string;
	vendor: string | null;
	categoryCode: string | null;
	salesUnit: string;
	claims: Claim[];
	labels: string[];
	deliveryReliability: number | null; // null = no history, not unreliable
	carbonFootprint: CarbonFootprint | null;
	claimsSource: 'SYNKKA' | 'MISSING';
}

// --- Policy (#13) ------------------------------------------------------------

/** A reason's `Severity`, widened to every outcome so one label table serves both. */
export type ReasonSeverity = PolicyOutcome | 'INFO';

// --- Mandates (#11) ----------------------------------------------------------

export type SubstitutionPolicy = 'NEVER' | 'IF_REQUIREMENTS_HOLD' | 'ALWAYS_NEEDS_APPROVAL';
export type AllergenStrictness = 'contains' | 'may_contain' | 'declared_free';

export interface Mandate {
	version: number;
	maxOrderTotal: Money;
	autoApproveUpTo: Money;
	periodSpendCap: Money;
	spendPeriod: 'WEEK' | 'MONTH';
	categorySpendCaps: { categoryCode: string; cap: Money }[];
	allowedCategoryCodes: string[];
	blockedCategoryCodes: string[];
	allowedVendors: string[];
	blockedVendors: string[];
	allowedCountriesOfOrigin: string[];
	requiredClaims: Claim[];
	requiredLabels: string[];
	requiredDiets: string[];
	excludedAllergens: string[];
	allergenStrictness: AllergenStrictness;
	substitutionPolicy: SubstitutionPolicy;
	maxSubstitutePriceIncreasePct: number | null;
	laterDeliveryNeedsApproval: boolean;
	minDeliveryReliability: number | null;
}

export interface PeriodSpend {
	periodStart: Iso;
	periodEnd: Iso;
	committed: Money;
	remaining: Money;
}

// --- Agents and keys (#22) ---------------------------------------------------

export type AgentStatus = 'ACTIVE' | 'DISABLED';

export interface AgentSummary {
	id: string;
	name: string;
	purpose: string;
	status: AgentStatus;
	mandate: Mandate;
	periodSpend: PeriodSpend;
	activeKeys: number;
	lastActiveAt: Iso | null;
}

export type KeyPreset = 'RESEARCH_ONLY' | 'PURCHASING';

export interface AgentKey {
	jti: string;
	prefix: string; // first characters, shown so people can tell keys apart
	label: string;
	scopes: string[];
	createdAt: Iso;
	createdBy: string;
	expiresAt: Iso;
	lastUsedAt: Iso | null;
	revokedAt: Iso | null;
}

export interface IssuedKey {
	key: AgentKey;
	/** The full key, returned once and never again. */
	secret: string;
}

export interface NewAgentInput {
	name: string;
	purpose: string;
	mandate: Omit<Mandate, 'version'>;
}

// --- Audit trail -------------------------------------------------------------

/** The query parameters of GET /api/v1/audit-events. */
export interface AuditFilter {
	/** Events of this agent, as actor or subject */
	agentId?: string;
	type?: AuditEventType;
	/** Events about this quote, order or agent */
	subject?: string;
	/** ISO date-time, inclusive */
	from?: Iso;
	/** ISO date-time, exclusive */
	to?: Iso;
}

/** An event in Valio Aimo's cross-customer feed, which only the mock serves so far. */
export type OversightEvent = AuditEvent & { organisationId: string; organisationName: string };

// --- Demo scenario controls --------------------------------------------------

export type ScenarioKind = 'OUT_OF_STOCK' | 'PARTIAL' | 'LATE' | 'PRICE_CHANGE';

export interface ScenarioOverride {
	id: string;
	productCode: string;
	productName: string;
	kind: ScenarioKind;
	detail: string;
	active: boolean;
}
