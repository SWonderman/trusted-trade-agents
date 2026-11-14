/**
 * Shapes shared by the server and the pages.
 *
 * Routes the backend already serves to people (sign-in, catalog) use types generated
 * from its OpenAPI schema into `backend.d.ts` (`npm run gen:api`); they are
 * re-exported below under short names. The rest mirror the contracts in GitHub
 * issues #11 (mandate), #13 (policy), #15 (orders) and #22 (agent keys) until those
 * routes land, then move to generated types too.
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

// --- Catalog and offers ------------------------------------------------------

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

export interface Conversion {
	requested: { amount: number; unit: 'L' | 'KG' | 'PCS' };
	buyerUnitsPerSalesUnit: number; // e.g. 20 (L per KI)
	salesUnits: number; // after rounding to lot size
	lotSize: number;
	rounded: boolean;
	method: 'COMPARISON_PRICE' | 'UNIT_CONVERSIONS' | 'NAME';
	crossCheck: 'AGREES' | 'DISAGREES' | 'UNCHECKED';
}

export interface OfferSnapshot {
	unitPrice: Money; // per sales unit
	comparisonPrice: Money; // per L or KG
	comparisonUnit: 'L' | 'KG';
	logisticModel: 'STOCK' | 'TERMINAL';
	availableAmount: number | null; // null = TERMINAL, quantity unknown
	availableDate: Iso; // ISO date
	closingTime: Iso; // ISO datetime
	priceValidTo: Iso;
	fetchedAt: Iso;
}

// --- Policy (#13) ------------------------------------------------------------

export type PolicyOutcome = 'AUTO_APPROVE' | 'NEEDS_HUMAN' | 'REJECT';
export type ReasonSeverity = PolicyOutcome | 'INFO';

export interface PolicyReason {
	code: string;
	severity: ReasonSeverity;
	lineRef?: string;
	message: string;
	facts: Record<string, string | number | boolean | null>;
}

export interface PolicyResult {
	outcome: PolicyOutcome;
	reasons: PolicyReason[];
	mandateVersion: number;
}

// --- Orders (#15) ------------------------------------------------------------

export type OrderStatus = 'PENDING_APPROVAL' | 'CONFIRMED' | 'APPROVED' | 'PLACED' | 'REJECTED';

export interface OrderLine {
	ref: string; // "L1", "L2"
	product: ProductRef;
	quantity: number; // sales units
	conversion: Conversion | null;
	offer: OfferSnapshot;
	lineTotal: Money;
	substitutesFor: ProductRef | null;
}

export interface StatusChange {
	status: OrderStatus;
	at: Iso;
	by: string; // "agent:dairy-restock" | "user:Helmi Virtanen" | "system"
	note?: string;
}

export interface LiveChange {
	lineRef: string;
	field: string;
	quoted: string | number;
	now: string | number;
}

export interface Order {
	orderId: string;
	quoteId: string;
	organisationId: string;
	organisationName: string;
	agent: { id: string; name: string };
	status: OrderStatus;
	buyerRequest: string | null;
	rationale: string | null;
	deliverBy: Iso;
	lines: OrderLine[];
	totals: { net: Money; vat: Money; gross: Money; deposits: Money };
	policy: PolicyResult;
	changes: LiveChange[];
	statusHistory: StatusChange[];
	createdAt: Iso;
	checkAgainAfterSeconds: number | null;
	approverNote: string | null;
}

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

export type ActorKind = 'agent' | 'user' | 'system';

export interface AuditEvent {
	id: string;
	at: Iso;
	organisationId: string;
	organisationName: string;
	actor: { kind: ActorKind; name: string };
	type: string; // TOOL_CALL, QUOTE_CREATED, ORDER_PENDING_APPROVAL, ORDER_APPROVED, KEY_ISSUED…
	tool?: string; // search_products, find_substitutes, create_quote, place_order…
	summary: string;
	orderId?: string;
	quoteId?: string;
	agentId?: string;
	outcome?: PolicyOutcome;
	reasonCodes?: string[];
	stateChange?: { from: string | null; to: string };
	/** Hash of the previous event, so tampering with history is detectable. */
	prevHash: string;
	hash: string;
}

export interface AuditFilter {
	agentId?: string;
	orderId?: string;
	type?: string;
	outcome?: PolicyOutcome;
}

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
