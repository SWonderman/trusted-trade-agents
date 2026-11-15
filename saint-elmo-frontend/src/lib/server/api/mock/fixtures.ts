/**
 * Seed data for the in-memory mock. It matches the demo seed described in
 * issue #11: a hotel chain with `dairy-restock` and a hospital kitchen with
 * `ward-kitchen`.
 *
 * Product 463038 (Valio Eila 10 l novobox, KI = 2 × ST ≈ 20 L) is taken from
 * the Valio Aimo catalog. The other product codes are illustrative until the
 * http implementation serves real catalog data.
 */
import type {
	AgentKey,
	AgentSummary,
	BuyerOrganisation,
	Mandate,
	Order,
	OrderLine,
	OrderStatus,
	PolicyOutcome,
	PolicyReason,
	ProductRef,
	ScenarioOverride,
	SessionUser
} from '#lib/api/types.js';

export const NOW = () => new Date();
export const minutesAgo = (m: number) => new Date(Date.now() - m * 60_000).toISOString();
export const daysFromNow = (d: number) => new Date(Date.now() + d * 86_400_000).toISOString();

/** The next Monday on or after tomorrow, as an ISO date: what "by Monday" resolves to. */
export function nextWeekday(day: number): string {
	const d = new Date();
	d.setUTCHours(0, 0, 0, 0);
	do d.setUTCDate(d.getUTCDate() + 1);
	while (d.getUTCDay() !== day);
	return d.toISOString().slice(0, 10);
}

function closingTimeBefore(isoDate: string) {
	const d = new Date(`${isoDate}T00:00:00Z`);
	d.setUTCDate(d.getUTCDate() - 1);
	d.setUTCHours(12, 0, 0, 0); // 14:00 Helsinki, the day before delivery
	return d.toISOString();
}

// --- Organisations and people -----------------------------------------------

export const ORGS: BuyerOrganisation[] = [
	{
		id: 'org-aurora',
		name: 'Aurora Hotels',
		kind: 'hotel_chain',
		customerNumber: 'DEMO-HOTEL-001'
	},
	{
		id: 'org-kuusikko',
		name: 'Kuusikko Hospital Kitchen',
		kind: 'hospital',
		customerNumber: 'DEMO-HOSPITAL-001'
	}
];

export const USERS: (SessionUser & { password: string })[] = [
	{
		id: 'u-helmi',
		name: 'Helmi Virtanen',
		email: 'buyer.admin@aurora-hotels.example',
		password: 'saint-elmo-demo',
		role: 'BUYER_ADMIN',
		organisation: ORGS[0]
	},
	{
		id: 'u-onni',
		name: 'Onni Korhonen',
		email: 'buyer.admin@kuusikko-hospital.example',
		password: 'saint-elmo-demo',
		role: 'BUYER_ADMIN',
		organisation: ORGS[1]
	},
	{
		id: 'u-satu',
		name: 'Satu Mäkelä',
		email: 'ops@valio-aimo.example',
		password: 'saint-elmo-demo',
		role: 'AIMO_STAFF',
		organisation: null
	}
];

// --- Products ---------------------------------------------------------------

export const PRODUCTS = {
	eila10: {
		code: '463038',
		name: 'Valio Eila® semi skimmed milk drink 10 l novobox lactose free',
		vendor: 'Valio',
		categoryCode: '10400',
		salesUnit: 'KI',
		claims: [{ type: 'FREE_FROM', element: 'LACTOSE' }],
		labels: ['MADE_IN_FINLAND_FLAG', 'COOL_TEMPERATURE'],
		deliveryReliability: 0.98,
		carbonFootprint: { value: 1.31, basis: 'PRODUCT_GROUP_AVERAGE' },
		claimsSource: 'SYNKKA'
	},
	lowLactose1l: {
		code: '464042',
		name: 'Valio Hyvä suomalainen Arki® semi skimmed milk drink 1 l',
		vendor: 'Valio',
		categoryCode: '10400',
		salesUnit: 'ST',
		claims: [],
		labels: ['COOL_TEMPERATURE'],
		deliveryReliability: 0.93,
		carbonFootprint: { value: 1.31, basis: 'PRODUCT_GROUP_AVERAGE' },
		claimsSource: 'SYNKKA'
	},
	butterLf: {
		code: '471280',
		name: 'Valio Egg & Butter spread 500 g lactose free',
		vendor: 'Valio',
		categoryCode: '10592',
		salesUnit: 'KI',
		claims: [{ type: 'FREE_FROM', element: 'LACTOSE' }],
		labels: ['MADE_IN_FINLAND_FLAG'],
		deliveryReliability: 1,
		carbonFootprint: { value: 9.8, basis: 'PRODUCT_GROUP_AVERAGE' },
		claimsSource: 'SYNKKA'
	},
	gfBread: {
		code: '474391',
		name: 'Oululainen Reissumies Gluten-Free Oat 3pcs 210g, oat bread',
		vendor: 'Fazer',
		categoryCode: '10901',
		salesUnit: 'ST',
		claims: [
			{ type: 'FREE_FROM', element: 'GLUTEN' },
			{ type: 'FREE_FROM', element: 'MILK' }
		],
		labels: ['HEART_SYMBOL'],
		deliveryReliability: null,
		carbonFootprint: { value: 1.12, basis: 'PRODUCT_GROUP_AVERAGE' },
		claimsSource: 'SYNKKA'
	},
	gfBreadOriginal: {
		code: '469602',
		name: 'Vaasan Moilas Free From dark gluten-free portion bread 280 g',
		vendor: 'Vaasan',
		categoryCode: '10900',
		salesUnit: 'ST',
		claims: [
			{ type: 'FREE_FROM', element: 'GLUTEN' },
			{ type: 'FREE_FROM', element: 'MILK' }
		],
		labels: [],
		deliveryReliability: 0.88,
		carbonFootprint: { value: 1.12, basis: 'PRODUCT_GROUP_AVERAGE' },
		claimsSource: 'SYNKKA'
	},
	muesli: {
		code: '465238',
		name: 'Fazer Alku Garden berries muesli 375 g',
		vendor: 'Fazer',
		categoryCode: '21373',
		salesUnit: 'PAK',
		claims: [],
		labels: [],
		deliveryReliability: 0.97,
		carbonFootprint: null,
		claimsSource: 'MISSING'
	},
	cream: {
		code: '464699',
		name: 'Valio whipping cream 1 l lactose free, organic',
		vendor: 'Valio',
		categoryCode: '10401',
		salesUnit: 'ST',
		claims: [{ type: 'FREE_FROM', element: 'LACTOSE' }],
		labels: ['MADE_IN_FINLAND_FLAG'],
		deliveryReliability: 0.99,
		carbonFootprint: { value: 4.2, basis: 'PRODUCT_GROUP_AVERAGE' },
		claimsSource: 'SYNKKA'
	}
} satisfies Record<string, ProductRef>;

// --- Mandates and agents ----------------------------------------------------

const emptyMandate: Omit<Mandate, 'version'> = {
	maxOrderTotal: 2000,
	autoApproveUpTo: 1000,
	periodSpendCap: 5000,
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
	substitutionPolicy: 'IF_REQUIREMENTS_HOLD',
	maxSubstitutePriceIncreasePct: 10,
	laterDeliveryNeedsApproval: true,
	minDeliveryReliability: null
};

export const MANDATES: Record<string, Mandate> = {
	'agt-dairy': {
		...emptyMandate,
		version: 4,
		maxOrderTotal: 2000,
		autoApproveUpTo: 1500,
		periodSpendCap: 5000,
		// Same dairy categories as the backend's demo seed (db/seeders/demo.py)
		allowedCategoryCodes: [
			'10400',
			'10401',
			'10404',
			'10405',
			'10411',
			'10412',
			'10419',
			'10430',
			'10500',
			'10501',
			'10600',
			'10602',
			'10603',
			'10630',
			'10631',
			'10632',
			'10633',
			'10635',
			'10636',
			'10637',
			'10639',
			'10640'
		],
		requiredClaims: [{ type: 'FREE_FROM', element: 'LACTOSE' }],
		substitutionPolicy: 'IF_REQUIREMENTS_HOLD',
		maxSubstitutePriceIncreasePct: 10,
		minDeliveryReliability: 0.9
	},
	'agt-event': {
		...emptyMandate,
		version: 2,
		maxOrderTotal: 3000,
		autoApproveUpTo: 800,
		periodSpendCap: 6000,
		spendPeriod: 'MONTH',
		substitutionPolicy: 'ALWAYS_NEEDS_APPROVAL',
		maxSubstitutePriceIncreasePct: null
	},
	'agt-ward': {
		...emptyMandate,
		version: 7,
		maxOrderTotal: 3000,
		autoApproveUpTo: 1000,
		periodSpendCap: 12000,
		spendPeriod: 'MONTH',
		excludedAllergens: ['AM', 'AW'],
		allergenStrictness: 'declared_free',
		substitutionPolicy: 'ALWAYS_NEEDS_APPROVAL',
		maxSubstitutePriceIncreasePct: 5,
		minDeliveryReliability: 0.85
	}
};

export const AGENTS: (Omit<AgentSummary, 'periodSpend' | 'activeKeys' | 'mandate'> & {
	organisationId: string;
})[] = [
	{
		id: 'agt-dairy',
		name: 'dairy-restock',
		purpose: 'Keeps the hotel kitchens stocked with lactose-free dairy.',
		status: 'ACTIVE',
		lastActiveAt: minutesAgo(9),
		organisationId: 'org-aurora'
	},
	{
		id: 'agt-event',
		name: 'event-planner',
		purpose: 'Sources everything for banquets and one-off events.',
		status: 'ACTIVE',
		lastActiveAt: minutesAgo(60 * 26),
		organisationId: 'org-aurora'
	},
	{
		id: 'agt-ward',
		name: 'ward-kitchen',
		purpose: 'Orders for patient meals under strict allergen rules.',
		status: 'ACTIVE',
		lastActiveAt: minutesAgo(41),
		organisationId: 'org-kuusikko'
	}
];

export const KEYS: Record<string, AgentKey[]> = {
	'agt-dairy': [
		{
			jti: 'k-7f2a',
			prefix: 'se_ag_7f2a',
			label: 'Claude Desktop, kitchen office',
			scopes: [
				'catalog:read',
				'offers:read',
				'mandate:read',
				'quote:create',
				'order:place',
				'order:read'
			],
			createdAt: minutesAgo(60 * 24 * 3),
			createdBy: 'Helmi Virtanen',
			expiresAt: daysFromNow(4),
			lastUsedAt: minutesAgo(9),
			revokedAt: null
		},
		{
			jti: 'k-19c0',
			prefix: 'se_ag_19c0',
			label: 'Old laptop',
			scopes: ['catalog:read', 'offers:read', 'mandate:read', 'order:read'],
			createdAt: minutesAgo(60 * 24 * 20),
			createdBy: 'Helmi Virtanen',
			expiresAt: daysFromNow(10),
			lastUsedAt: minutesAgo(60 * 24 * 12),
			revokedAt: minutesAgo(60 * 24 * 11)
		}
	],
	'agt-event': [
		{
			jti: 'k-a3d9',
			prefix: 'se_ag_a3d9',
			label: 'Events team script',
			scopes: [
				'catalog:read',
				'offers:read',
				'mandate:read',
				'quote:create',
				'order:place',
				'order:read'
			],
			createdAt: minutesAgo(60 * 24 * 6),
			createdBy: 'Helmi Virtanen',
			expiresAt: daysFromNow(1),
			lastUsedAt: minutesAgo(60 * 26),
			revokedAt: null
		}
	],
	'agt-ward': [
		{
			jti: 'k-5be1',
			prefix: 'se_ag_5be1',
			label: 'Ward kitchen tablet',
			scopes: [
				'catalog:read',
				'offers:read',
				'mandate:read',
				'quote:create',
				'order:place',
				'order:read'
			],
			createdAt: minutesAgo(60 * 24 * 2),
			createdBy: 'Onni Korhonen',
			expiresAt: daysFromNow(5),
			lastUsedAt: minutesAgo(41),
			revokedAt: null
		}
	]
};

// --- Orders -----------------------------------------------------------------

const TAX_RATE = 13.5; // food VAT in Finland, percent
const round2 = (v: number) => Math.round(v * 100) / 100;
export const withTax = (net: number) => ({
	net: round2(net),
	gross: round2(net * (1 + TAX_RATE / 100))
});

const SEVERITY_RANK = { INFO: 0, NEEDS_HUMAN: 1, REJECT: 2 } as const;

/** The most severe outcome of some reasons, as the backend's policy judges it. */
export function outcomeOf(reasons: PolicyReason[]): PolicyOutcome {
	const worst = reasons.reduce<PolicyReason['severity']>(
		(w, r) => (SEVERITY_RANK[r.severity] > SEVERITY_RANK[w] ? r.severity : w),
		'INFO'
	);
	return worst === 'INFO' ? 'AUTO_APPROVE' : worst;
}

/** An order as the mock stores it: the backend's shape, plus its buyer organisation. */
export type MockOrder = Order & { organisationId: string };

interface LineSpec {
	product: ProductRef;
	salesUnits: number;
	/** What the agent asked for in the buyer's unit, when it wasn't in sales units. */
	requested?: { value: number; unit: 'L' | 'KG' | 'PCS'; perSalesUnit: number };
	lotSize?: number;
	unitPrice: number; // net per sales unit
	comparisonPrice: number | null; // net per L or KG
	comparisonUnit?: 'L' | 'KG';
	logisticModel: 'STOCK' | 'TERMINAL';
	availableAmount: number | null; // null = TERMINAL, unknown
	earliestDate: string;
	priceValidTo: string;
	fetchedAt: string;
	substitutesFor?: ProductRef;
	reasons?: Omit<PolicyReason, 'lineRef'>[];
}

/** One judged line, in the backend's `JudgedLineOut` shape. */
function line(position: number, deliverBy: string, spec: LineSpec): OrderLine {
	const r = spec.requested;
	const closingTime = closingTimeBefore(spec.earliestDate);
	const reasons = (spec.reasons ?? []).map((x) => ({ ...x, lineRef: String(position) }));
	return {
		productCode: spec.product.code,
		name: spec.product.name,
		salesUnit: spec.product.salesUnit,
		price: {
			perSalesUnit: withTax(spec.unitPrice),
			taxRate: TAX_RATE,
			currency: 'EUR',
			comparisonPrice:
				spec.comparisonPrice === null
					? null
					: { value: spec.comparisonPrice, unit: spec.comparisonUnit ?? 'L' },
			customerSpecific: true,
			validFrom: null,
			validTo: spec.priceValidTo
		},
		availability: {
			logisticModel: spec.logisticModel,
			availableAmount: spec.availableAmount,
			availableAmountKnown: spec.availableAmount !== null,
			earliestDate: spec.earliestDate,
			closingTime,
			salesBlocked: false,
			meetsDeadline: spec.earliestDate <= deliverBy && new Date(closingTime).getTime() > Date.now()
		},
		quantity: {
			requested: r
				? { value: r.value, unit: r.unit }
				: { value: spec.salesUnits, unit: spec.product.salesUnit },
			conversion: r
				? {
						perSalesUnit: { value: r.perSalesUnit, unit: r.unit },
						basis: r.unit === 'PCS' ? 'PACKAGING_UNITS' : 'PRICE_COMPARISON',
						crossCheck: 'AGREES'
					}
				: null,
			salesUnits: spec.salesUnits,
			lotSize: spec.lotSize ?? 1,
			roundedUp: r ? spec.salesUnits * r.perSalesUnit > r.value : false,
			delivered: r ? { value: spec.salesUnits * r.perSalesUnit, unit: r.unit } : null,
			lineTotal: withTax(spec.salesUnits * spec.unitPrice),
			coveredByAvailability:
				spec.availableAmount === null ? null : spec.availableAmount >= spec.salesUnits
		},
		deliveryReliability: spec.product.deliveryReliability,
		carbonFootprint: spec.product.carbonFootprint,
		reasonCodes: [],
		provenance: {
			source: 'Demo fixtures',
			fetchedAt: spec.fetchedAt,
			validUntil: closingTime,
			cached: false
		},
		position,
		substitutesFor: spec.substitutesFor?.code ?? null,
		outcome: outcomeOf(reasons),
		reasons
	};
}

interface OrderSpec {
	orderId: string;
	quoteId: string;
	organisationId: string;
	agent: { id: string; name: string };
	status: OrderStatus;
	buyerRequest: string;
	rationale: string;
	deliverBy: string;
	lines: LineSpec[];
	/** The order's own reasons, after the lines'. */
	reasons?: PolicyReason[];
	mandateVersion: number;
	changes?: Order['changes'];
	statusHistory: Order['statusHistory'];
	createdAt: string;
}

/** Totals and the policy's summary, derived from the lines like the backend does. */
export function judged(order: MockOrder, lines: OrderLine[], own: PolicyReason[] = []): MockOrder {
	const reasons = [...lines.flatMap((l) => l.reasons), ...own];
	const net = lines.reduce((sum, l) => sum + (l.quantity?.lineTotal?.net ?? 0), 0);
	const gross = lines.reduce((sum, l) => sum + (l.quantity?.lineTotal?.gross ?? 0), 0);
	return {
		...order,
		lines,
		totals: { net: round2(net), gross: round2(gross), currency: 'EUR' },
		policy: { ...order.policy, outcome: outcomeOf(reasons), reasons }
	};
}

function order(spec: OrderSpec): MockOrder {
	const lines = spec.lines.map((l, i) => line(i + 1, spec.deliverBy, l));
	const base: MockOrder = {
		orderId: spec.orderId,
		quoteId: spec.quoteId,
		organisationId: spec.organisationId,
		status: spec.status,
		createdAt: spec.createdAt,
		agent: spec.agent,
		deliverBy: spec.deliverBy,
		lines: [],
		totals: { net: 0, gross: 0, currency: 'EUR' },
		deposits: [],
		policy: { outcome: 'AUTO_APPROVE', reasons: [], mandateVersion: spec.mandateVersion },
		changes: spec.changes ?? [],
		buyerRequest: spec.buyerRequest,
		rationale: spec.rationale,
		statusHistory: spec.statusHistory,
		approverNote: null,
		decidedAt: null,
		checkAgainAfterSeconds: spec.status === 'PENDING_APPROVAL' ? 30 : null
	};
	return judged(base, lines, spec.reasons);
}

export function buildOrders(): MockOrder[] {
	const monday = nextWeekday(1);
	const wednesday = nextWeekday(3);
	const tuesday = nextWeekday(2);
	const saturday = nextWeekday(6);
	const dairy = { id: 'agt-dairy', name: 'dairy-restock' };

	return [
		order({
			orderId: 'e2372b01-ed8f-488c-9e2e-35d678b43216',
			quoteId: 'e9ecccd9-141a-4e0e-835d-e3fceffaacb9',
			organisationId: 'org-aurora',
			agent: dairy,
			status: 'PENDING_APPROVAL',
			buyerRequest:
				'I need 1,000 litres of lactose-free milk by Monday. Find an option that meets our requirements based on price and availability.',
			rationale:
				'Compared four lactose-free milk products. Eila 10 l novobox is the cheapest per litre (€1.84/L) and the only one with 50 cases in Aimo’s own stock for Monday. The 1 l cartons cost €0.27/L more and would add 1,000 packages to unpack. The total is over the auto-approve limit, so I am asking for sign-off rather than splitting the order.',
			deliverBy: monday,
			lines: [
				{
					product: PRODUCTS.eila10,
					salesUnits: 50,
					requested: { value: 1000, unit: 'L', perSalesUnit: 20 },
					unitPrice: 36.8,
					comparisonPrice: 1.84,
					logisticModel: 'STOCK',
					availableAmount: 64,
					earliestDate: monday,
					priceValidTo: daysFromNow(2),
					fetchedAt: minutesAgo(2)
				}
			],
			reasons: [
				{
					code: 'OVER_AUTO_APPROVE_LIMIT',
					severity: 'NEEDS_HUMAN',
					lineRef: null,
					message:
						'The order total of €1,840 is over the €1,500 auto-approve limit. The order limit is €2,000.',
					facts: { orderTotal: 1840, autoApproveUpTo: 1500, maxOrderTotal: 2000 }
				}
			],
			mandateVersion: 4,
			statusHistory: [{ status: 'PENDING_APPROVAL', at: minutesAgo(9), by: 'agent:dairy-restock' }],
			createdAt: minutesAgo(9)
		}),
		order({
			orderId: 'e1406fb1-3bfc-4491-914e-88b6abdd2184',
			quoteId: '6ab13e08-f159-4b76-9c37-1cddb74d640e',
			organisationId: 'org-aurora',
			agent: dairy,
			status: 'PENDING_APPROVAL',
			buyerRequest: '400 L of lactose-free milk for the Wednesday breakfast buffets.',
			rationale:
				'Only 12 cases of Eila 10 l are available for Wednesday (240 L). I took all of it and covered the remaining 160 L with the regular 1 l Arki carton, which is cheaper and in stock. It is not declared lactose-free, so a person has to decide whether regular milk is acceptable for the buffet. The alternative is moving 160 L to Thursday.',
			deliverBy: wednesday,
			lines: [
				{
					product: PRODUCTS.eila10,
					salesUnits: 12,
					requested: { value: 240, unit: 'L', perSalesUnit: 20 },
					unitPrice: 36.8,
					comparisonPrice: 1.84,
					logisticModel: 'STOCK',
					availableAmount: 12,
					earliestDate: wednesday,
					priceValidTo: daysFromNow(2),
					fetchedAt: minutesAgo(31)
				},
				{
					product: PRODUCTS.lowLactose1l,
					salesUnits: 168,
					requested: { value: 160, unit: 'L', perSalesUnit: 1 },
					lotSize: 12,
					unitPrice: 1.42,
					comparisonPrice: 1.42,
					logisticModel: 'STOCK',
					availableAmount: 600,
					earliestDate: wednesday,
					priceValidTo: daysFromNow(2),
					fetchedAt: minutesAgo(31),
					substitutesFor: PRODUCTS.eila10,
					reasons: [
						{
							code: 'MISSING_REQUIRED_CLAIM',
							severity: 'NEEDS_HUMAN',
							message:
								'The substitute is not declared lactose-free. It makes no lactose claim at all, and the mandate requires FREE_FROM_LACTOSE.',
							facts: { required: 'FREE_FROM LACTOSE', declared: 'none', source: 'Synkka' }
						},
						{
							code: 'ROUNDED_TO_LOT_SIZE',
							severity: 'INFO',
							message:
								'160 cartons were rounded up to 168, because this product is sold in multiples of 12.',
							facts: { requested: 160, ordered: 168, lotSize: 12 }
						}
					]
				}
			],
			mandateVersion: 4,
			statusHistory: [
				{ status: 'PENDING_APPROVAL', at: minutesAgo(31), by: 'agent:dairy-restock' }
			],
			createdAt: minutesAgo(31)
		}),
		order({
			orderId: '7e6f63ce-34c1-4e87-ac0d-e8b6b1cfda37',
			quoteId: '1a62c2ed-1e2b-4f91-8812-6fd3aa563081',
			organisationId: 'org-kuusikko',
			agent: { id: 'agt-ward', name: 'ward-kitchen' },
			status: 'PENDING_APPROVAL',
			buyerRequest: 'Gluten- and milk-free bread for 140 patients for Tuesday.',
			rationale:
				'The usual dark bread (377815) is out of stock until next week. The oat bread is also declared free from gluten and milk by the manufacturer. Its earliest delivery is Wednesday, one day late; the ward has two days of buffer stock, so I recommend accepting the later date.',
			deliverBy: tuesday,
			lines: [
				{
					product: PRODUCTS.gfBread,
					salesUnits: 70,
					unitPrice: 4.35,
					comparisonPrice: 14.5,
					comparisonUnit: 'KG',
					logisticModel: 'TERMINAL',
					availableAmount: null,
					earliestDate: wednesday,
					priceValidTo: daysFromNow(3),
					fetchedAt: minutesAgo(44),
					substitutesFor: PRODUCTS.gfBreadOriginal,
					reasons: [
						{
							code: 'SUBSTITUTE_NEEDS_APPROVAL',
							severity: 'NEEDS_HUMAN',
							message: 'This mandate sends every substitute to a person.',
							facts: { substitutionPolicy: 'ALWAYS_NEEDS_APPROVAL' }
						},
						{
							code: 'LATE_DELIVERY',
							severity: 'NEEDS_HUMAN',
							message: 'The earliest delivery is one day after the requested date.',
							facts: { deliverBy: tuesday, earliest: wednesday, daysLate: 1 }
						},
						{
							code: 'STOCK_UNKNOWN',
							severity: 'INFO',
							message:
								'Shipped from the supplier’s warehouse, so the available quantity cannot be confirmed.',
							facts: { logisticModel: 'TERMINAL' }
						}
					]
				}
			],
			mandateVersion: 7,
			changes: [{ lineRef: '1', field: 'unitPrice', quoted: 4.29, now: 4.35 }],
			statusHistory: [{ status: 'PENDING_APPROVAL', at: minutesAgo(44), by: 'agent:ward-kitchen' }],
			createdAt: minutesAgo(44)
		}),
		order({
			orderId: 'e75e222d-3fc0-43d6-aae6-b0f85629f69d',
			quoteId: 'ca6f9dd2-9cb6-494e-b159-b2736de440da',
			organisationId: 'org-aurora',
			agent: dairy,
			status: 'PLACED',
			buyerRequest: 'Top up lactose-free butter, about 40 kg.',
			rationale: 'Same product as last week, within limits, in stock for Monday.',
			deliverBy: monday,
			lines: [
				{
					product: PRODUCTS.butterLf,
					salesUnits: 8,
					requested: { value: 40, unit: 'KG', perSalesUnit: 5 },
					unitPrice: 51.5,
					comparisonPrice: 10.3,
					comparisonUnit: 'KG',
					logisticModel: 'STOCK',
					availableAmount: 120,
					earliestDate: monday,
					priceValidTo: daysFromNow(2),
					fetchedAt: minutesAgo(60 * 5)
				}
			],
			mandateVersion: 4,
			statusHistory: [
				{ status: 'CONFIRMED', at: minutesAgo(60 * 5), by: 'agent:dairy-restock' },
				{ status: 'PLACED', at: minutesAgo(60 * 5), by: 'system' }
			],
			createdAt: minutesAgo(60 * 5)
		}),
		order({
			orderId: '2bc108e1-888f-4705-bc1e-49cb10126755',
			quoteId: '80114510-a77f-42f0-8c53-5dcca5f5b336',
			organisationId: 'org-aurora',
			agent: { id: 'agt-event', name: 'event-planner' },
			status: 'REJECTED',
			buyerRequest: 'Cream and cheese for the 300-guest wedding on Saturday.',
			rationale: 'Bundled everything for the wedding into one order.',
			deliverBy: saturday,
			lines: [
				{
					product: PRODUCTS.cream,
					salesUnits: 720,
					requested: { value: 720, unit: 'L', perSalesUnit: 1 },
					lotSize: 6,
					unitPrice: 4.75,
					comparisonPrice: 4.75,
					logisticModel: 'STOCK',
					availableAmount: 900,
					earliestDate: saturday,
					priceValidTo: daysFromNow(3),
					fetchedAt: minutesAgo(60 * 26)
				}
			],
			reasons: [
				{
					code: 'OVER_ORDER_LIMIT',
					severity: 'REJECT',
					lineRef: null,
					message: 'The order total of €3,420 is over the €3,000 order limit.',
					facts: { orderTotal: 3420, maxOrderTotal: 3000 }
				}
			],
			mandateVersion: 2,
			statusHistory: [{ status: 'REJECTED', at: minutesAgo(60 * 26), by: 'agent:event-planner' }],
			createdAt: minutesAgo(60 * 26)
		}),
		order({
			orderId: '9df6a8ff-3ec0-4244-9461-022700cce945',
			quoteId: '4fb14cae-b26e-45aa-84e1-ed66b5b731a6',
			organisationId: 'org-kuusikko',
			agent: { id: 'agt-ward', name: 'ward-kitchen' },
			status: 'REJECTED',
			buyerRequest: 'Breakfast muesli for the cardiology ward.',
			rationale: 'Cheapest muesli in stock.',
			deliverBy: tuesday,
			lines: [
				{
					product: PRODUCTS.muesli,
					salesUnits: 6,
					unitPrice: 11.9,
					comparisonPrice: 4.76,
					comparisonUnit: 'KG',
					logisticModel: 'STOCK',
					availableAmount: 40,
					earliestDate: tuesday,
					priceValidTo: daysFromNow(3),
					fetchedAt: minutesAgo(60 * 30),
					reasons: [
						{
							code: 'ALLERGEN_NOT_DECLARED_FREE',
							severity: 'REJECT',
							message:
								'The manufacturer has not declared this product free from milk or gluten cereals. Missing data counts as not free-from.',
							facts: { excluded: 'AM, AW', declared: 'none', source: 'missing' }
						}
					]
				}
			],
			mandateVersion: 7,
			statusHistory: [{ status: 'REJECTED', at: minutesAgo(60 * 30), by: 'agent:ward-kitchen' }],
			createdAt: minutesAgo(60 * 30)
		})
	];
}

export const SCENARIOS: ScenarioOverride[] = [
	{
		id: 'sc-1',
		productCode: '463038',
		productName: PRODUCTS.eila10.name,
		kind: 'PARTIAL',
		detail: 'Only 12 KI available for Wednesday',
		active: true
	},
	{
		id: 'sc-2',
		productCode: '469602',
		productName: PRODUCTS.gfBreadOriginal.name,
		kind: 'OUT_OF_STOCK',
		detail: 'Out of stock until next week',
		active: true
	},
	{
		id: 'sc-3',
		productCode: '463038',
		productName: PRODUCTS.eila10.name,
		kind: 'OUT_OF_STOCK',
		detail: 'Out of stock from Wednesday',
		active: false
	},
	{
		id: 'sc-4',
		productCode: '471280',
		productName: PRODUCTS.butterLf.name,
		kind: 'PRICE_CHANGE',
		detail: 'Price up 8% at the next re-check',
		active: false
	}
];
