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
	{ id: 'org-kajo', name: 'Kajo Hotels', kind: 'hotel_chain', customerNumber: '100482' },
	{
		id: 'org-merikoski',
		name: 'Merikoski Hospital kitchen',
		kind: 'hospital',
		customerNumber: '100917'
	}
];

export const USERS: (SessionUser & { password: string })[] = [
	{
		id: 'u-aino',
		name: 'Aino Virtanen',
		email: 'aino@kajohotels.demo',
		password: 'demo',
		role: 'buyer_admin',
		organisation: ORGS[0]
	},
	{
		id: 'u-mikael',
		name: 'Mikael Laine',
		email: 'mikael@merikoski.demo',
		password: 'demo',
		role: 'buyer_admin',
		organisation: ORGS[1]
	},
	{
		id: 'u-satu',
		name: 'Satu Korhonen',
		email: 'satu@aimo-ops.demo',
		password: 'demo',
		role: 'aimo_staff',
		organisation: null
	}
];

// --- Products ---------------------------------------------------------------

export const PRODUCTS = {
	eila10: {
		code: '463038',
		name: 'Valio Eila® semi skimmed milk drink 10 l novobox lactose free',
		vendor: 'Valio',
		categoryCode: '1101',
		salesUnit: 'KI',
		claims: [{ type: 'FREE_FROM', element: 'LACTOSE' }],
		labels: ['MADE_IN_FINLAND_FLAG', 'COOL_TEMPERATURE'],
		deliveryReliability: 0.98,
		carbonFootprint: { value: 1.31, basis: 'PRODUCT_GROUP_AVERAGE' },
		claimsSource: 'SYNKKA'
	},
	lowLactose1l: {
		code: '418207',
		name: 'Semi skimmed milk drink 1 l low lactose',
		vendor: 'Arla',
		categoryCode: '1101',
		salesUnit: 'ST',
		claims: [{ type: 'LOW', element: 'LACTOSE' }],
		labels: ['COOL_TEMPERATURE'],
		deliveryReliability: 0.93,
		carbonFootprint: { value: 1.31, basis: 'PRODUCT_GROUP_AVERAGE' },
		claimsSource: 'SYNKKA'
	},
	butterLf: {
		code: '402115',
		name: 'Lactose-free butter 500 g',
		vendor: 'Valio',
		categoryCode: '1104',
		salesUnit: 'KI',
		claims: [{ type: 'FREE_FROM', element: 'LACTOSE' }],
		labels: ['MADE_IN_FINLAND_FLAG'],
		deliveryReliability: 1,
		carbonFootprint: { value: 9.8, basis: 'PRODUCT_GROUP_AVERAGE' },
		claimsSource: 'SYNKKA'
	},
	gfBread: {
		code: '377920',
		name: 'Gluten-free oat bread 300 g, sliced',
		vendor: 'Fazer',
		categoryCode: '2203',
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
		code: '377815',
		name: 'Gluten-free dark bread 330 g, sliced',
		vendor: 'Fazer',
		categoryCode: '2203',
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
		code: '361044',
		name: 'Berry muesli 2.5 kg',
		vendor: 'Myllärin',
		categoryCode: '2401',
		salesUnit: 'PAK',
		claims: [],
		labels: [],
		deliveryReliability: 0.97,
		carbonFootprint: null,
		claimsSource: 'MISSING'
	},
	cream: {
		code: '409876',
		name: 'Whipping cream 38% 1 l lactose free',
		vendor: 'Valio',
		categoryCode: '1102',
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
		allowedCategoryCodes: ['1101', '1102', '1103', '1104'],
		requiredClaims: [{ type: 'FREE_FROM', element: 'LACTOSE' }],
		substitutionPolicy: 'IF_REQUIREMENTS_HOLD',
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
		maxOrderTotal: 2500,
		autoApproveUpTo: 1000,
		periodSpendCap: 8000,
		excludedAllergens: ['AM', 'AW'],
		allergenStrictness: 'declared_free',
		substitutionPolicy: 'ALWAYS_NEEDS_APPROVAL',
		maxSubstitutePriceIncreasePct: 15,
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
		organisationId: 'org-kajo'
	},
	{
		id: 'agt-event',
		name: 'event-planner',
		purpose: 'Sources everything for banquets and one-off events.',
		status: 'ACTIVE',
		lastActiveAt: minutesAgo(60 * 26),
		organisationId: 'org-kajo'
	},
	{
		id: 'agt-ward',
		name: 'ward-kitchen',
		purpose: 'Orders for patient meals under strict allergen rules.',
		status: 'ACTIVE',
		lastActiveAt: minutesAgo(41),
		organisationId: 'org-merikoski'
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
			createdBy: 'Aino Virtanen',
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
			createdBy: 'Aino Virtanen',
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
			createdBy: 'Aino Virtanen',
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
			createdBy: 'Mikael Laine',
			expiresAt: daysFromNow(5),
			lastUsedAt: minutesAgo(41),
			revokedAt: null
		}
	]
};

// --- Orders -----------------------------------------------------------------

const VAT = 0.135; // food VAT in Finland, applied to keep totals realistic

function totals(net: number, deposits = 0) {
	const vat = Math.round(net * VAT * 100) / 100;
	return { net, vat, gross: Math.round((net + vat) * 100) / 100, deposits };
}

export function buildOrders(): Order[] {
	const monday = nextWeekday(1);
	const wednesday = nextWeekday(3);
	const tuesday = nextWeekday(2);

	return [
		{
			orderId: 'ORD-0142',
			quoteId: 'Q-0398',
			organisationId: 'org-kajo',
			organisationName: 'Kajo Hotels',
			agent: { id: 'agt-dairy', name: 'dairy-restock' },
			status: 'PENDING_APPROVAL',
			buyerRequest:
				'I need 1,000 litres of lactose-free milk by Monday. Find an option that meets our requirements based on price and availability.',
			rationale:
				'Compared four lactose-free milk products. Eila 10 l novobox is the cheapest per litre (€1.84/L) and the only one with 50 cases in Aimo’s own stock for Monday. The 1 l cartons cost €0.27/L more and would add 1,000 packages to unpack. The total is over the auto-approve limit, so I am asking for sign-off rather than splitting the order.',
			deliverBy: monday,
			lines: [
				{
					ref: 'L1',
					product: PRODUCTS.eila10,
					quantity: 50,
					conversion: {
						requested: { amount: 1000, unit: 'L' },
						buyerUnitsPerSalesUnit: 20,
						salesUnits: 50,
						lotSize: 1,
						rounded: false,
						method: 'COMPARISON_PRICE',
						crossCheck: 'AGREES'
					},
					offer: {
						unitPrice: 36.8,
						comparisonPrice: 1.84,
						comparisonUnit: 'L',
						logisticModel: 'STOCK',
						availableAmount: 64,
						availableDate: monday,
						closingTime: closingTimeBefore(monday),
						priceValidTo: daysFromNow(2),
						fetchedAt: minutesAgo(2)
					},
					lineTotal: 1840,
					substitutesFor: null
				}
			],
			totals: totals(1840),
			policy: {
				outcome: 'NEEDS_HUMAN',
				mandateVersion: 4,
				reasons: [
					{
						code: 'OVER_AUTO_APPROVE_LIMIT',
						severity: 'NEEDS_HUMAN',
						message:
							'The order total of €1,840 is over the €1,500 auto-approve limit. The order limit is €2,000.',
						facts: { orderTotal: 1840, autoApproveUpTo: 1500, maxOrderTotal: 2000 }
					}
				]
			},
			changes: [],
			statusHistory: [{ status: 'PENDING_APPROVAL', at: minutesAgo(9), by: 'agent:dairy-restock' }],
			createdAt: minutesAgo(9),
			checkAgainAfterSeconds: 30,
			approverNote: null
		},
		{
			orderId: 'ORD-0139',
			quoteId: 'Q-0391',
			organisationId: 'org-kajo',
			organisationName: 'Kajo Hotels',
			agent: { id: 'agt-dairy', name: 'dairy-restock' },
			status: 'PENDING_APPROVAL',
			buyerRequest: '400 L of lactose-free milk for the Wednesday breakfast buffets.',
			rationale:
				'Only 12 cases of Eila 10 l are available for Wednesday (240 L). I took all of it and covered the remaining 160 L with the 1 l low-lactose carton, which is cheaper and in stock. It is not declared lactose-free, so a person has to decide whether low-lactose is acceptable for the buffet. The alternative is moving 160 L to Thursday.',
			deliverBy: wednesday,
			lines: [
				{
					ref: 'L1',
					product: PRODUCTS.eila10,
					quantity: 12,
					conversion: {
						requested: { amount: 240, unit: 'L' },
						buyerUnitsPerSalesUnit: 20,
						salesUnits: 12,
						lotSize: 1,
						rounded: false,
						method: 'COMPARISON_PRICE',
						crossCheck: 'AGREES'
					},
					offer: {
						unitPrice: 36.8,
						comparisonPrice: 1.84,
						comparisonUnit: 'L',
						logisticModel: 'STOCK',
						availableAmount: 12,
						availableDate: wednesday,
						closingTime: closingTimeBefore(wednesday),
						priceValidTo: daysFromNow(2),
						fetchedAt: minutesAgo(31)
					},
					lineTotal: 441.6,
					substitutesFor: null
				},
				{
					ref: 'L2',
					product: PRODUCTS.lowLactose1l,
					quantity: 168,
					conversion: {
						requested: { amount: 160, unit: 'L' },
						buyerUnitsPerSalesUnit: 1,
						salesUnits: 168,
						lotSize: 12,
						rounded: true,
						method: 'COMPARISON_PRICE',
						crossCheck: 'AGREES'
					},
					offer: {
						unitPrice: 1.42,
						comparisonPrice: 1.42,
						comparisonUnit: 'L',
						logisticModel: 'STOCK',
						availableAmount: 600,
						availableDate: wednesday,
						closingTime: closingTimeBefore(wednesday),
						priceValidTo: daysFromNow(2),
						fetchedAt: minutesAgo(31)
					},
					lineTotal: 238.56,
					substitutesFor: PRODUCTS.eila10
				}
			],
			totals: totals(680.16),
			policy: {
				outcome: 'NEEDS_HUMAN',
				mandateVersion: 4,
				reasons: [
					{
						code: 'MISSING_REQUIRED_CLAIM',
						severity: 'NEEDS_HUMAN',
						lineRef: 'L2',
						message:
							'The substitute is not declared lactose-free. It is labelled low-lactose, and the mandate requires FREE_FROM_LACTOSE.',
						facts: { required: 'FREE_FROM LACTOSE', declared: 'LOW LACTOSE', source: 'Synkka' }
					},
					{
						code: 'ROUNDED_TO_LOT_SIZE',
						severity: 'INFO',
						lineRef: 'L2',
						message:
							'160 cartons were rounded up to 168, because this product is sold in multiples of 12.',
						facts: { requested: 160, ordered: 168, lotSize: 12 }
					}
				]
			},
			changes: [],
			statusHistory: [
				{ status: 'PENDING_APPROVAL', at: minutesAgo(31), by: 'agent:dairy-restock' }
			],
			createdAt: minutesAgo(31),
			checkAgainAfterSeconds: 30,
			approverNote: null
		},
		{
			orderId: 'ORD-0137',
			quoteId: 'Q-0385',
			organisationId: 'org-merikoski',
			organisationName: 'Merikoski Hospital kitchen',
			agent: { id: 'agt-ward', name: 'ward-kitchen' },
			status: 'PENDING_APPROVAL',
			buyerRequest: 'Gluten- and milk-free bread for 140 patients for Tuesday.',
			rationale:
				'The usual dark bread (377815) is out of stock until next week. The oat bread is also declared free from gluten and milk by the manufacturer. Its earliest delivery is Wednesday, one day late; the ward has two days of buffer stock, so I recommend accepting the later date.',
			deliverBy: tuesday,
			lines: [
				{
					ref: 'L1',
					product: PRODUCTS.gfBread,
					quantity: 70,
					conversion: null,
					offer: {
						unitPrice: 4.35,
						comparisonPrice: 14.5,
						comparisonUnit: 'KG',
						logisticModel: 'TERMINAL',
						availableAmount: null,
						availableDate: wednesday,
						closingTime: closingTimeBefore(wednesday),
						priceValidTo: daysFromNow(3),
						fetchedAt: minutesAgo(44)
					},
					lineTotal: 304.5,
					substitutesFor: PRODUCTS.gfBreadOriginal
				}
			],
			totals: totals(304.5),
			policy: {
				outcome: 'NEEDS_HUMAN',
				mandateVersion: 7,
				reasons: [
					{
						code: 'SUBSTITUTE_NEEDS_APPROVAL',
						severity: 'NEEDS_HUMAN',
						lineRef: 'L1',
						message: 'This mandate sends every substitute to a person.',
						facts: { substitutionPolicy: 'ALWAYS_NEEDS_APPROVAL' }
					},
					{
						code: 'LATE_DELIVERY',
						severity: 'NEEDS_HUMAN',
						lineRef: 'L1',
						message: 'The earliest delivery is one day after the requested date.',
						facts: { deliverBy: tuesday, earliest: wednesday, daysLate: 1 }
					},
					{
						code: 'STOCK_UNKNOWN',
						severity: 'INFO',
						lineRef: 'L1',
						message:
							'Shipped from the supplier’s warehouse, so the available quantity cannot be confirmed.',
						facts: { logisticModel: 'TERMINAL' }
					}
				]
			},
			changes: [{ lineRef: 'L1', field: 'unitPrice', quoted: 4.29, now: 4.35 }],
			statusHistory: [{ status: 'PENDING_APPROVAL', at: minutesAgo(44), by: 'agent:ward-kitchen' }],
			createdAt: minutesAgo(44),
			checkAgainAfterSeconds: 30,
			approverNote: null
		},
		{
			orderId: 'ORD-0131',
			quoteId: 'Q-0377',
			organisationId: 'org-kajo',
			organisationName: 'Kajo Hotels',
			agent: { id: 'agt-dairy', name: 'dairy-restock' },
			status: 'PLACED',
			buyerRequest: 'Top up lactose-free butter, about 40 kg.',
			rationale: 'Same product as last week, within limits, in stock for Monday.',
			deliverBy: monday,
			lines: [
				{
					ref: 'L1',
					product: PRODUCTS.butterLf,
					quantity: 8,
					conversion: {
						requested: { amount: 40, unit: 'KG' },
						buyerUnitsPerSalesUnit: 5,
						salesUnits: 8,
						lotSize: 1,
						rounded: false,
						method: 'UNIT_CONVERSIONS',
						crossCheck: 'AGREES'
					},
					offer: {
						unitPrice: 51.5,
						comparisonPrice: 10.3,
						comparisonUnit: 'KG',
						logisticModel: 'STOCK',
						availableAmount: 120,
						availableDate: monday,
						closingTime: closingTimeBefore(monday),
						priceValidTo: daysFromNow(2),
						fetchedAt: minutesAgo(60 * 5)
					},
					lineTotal: 412,
					substitutesFor: null
				}
			],
			totals: totals(412),
			policy: { outcome: 'AUTO_APPROVE', mandateVersion: 4, reasons: [] },
			changes: [],
			statusHistory: [
				{ status: 'CONFIRMED', at: minutesAgo(60 * 5), by: 'system' },
				{ status: 'PLACED', at: minutesAgo(60 * 5), by: 'system' }
			],
			createdAt: minutesAgo(60 * 5),
			checkAgainAfterSeconds: null,
			approverNote: null
		},
		{
			orderId: 'ORD-0128',
			quoteId: 'Q-0370',
			organisationId: 'org-kajo',
			organisationName: 'Kajo Hotels',
			agent: { id: 'agt-event', name: 'event-planner' },
			status: 'REJECTED',
			buyerRequest: 'Cream and cheese for the 300-guest wedding on Saturday.',
			rationale: 'Bundled everything for the wedding into one order.',
			deliverBy: nextWeekday(6),
			lines: [
				{
					ref: 'L1',
					product: PRODUCTS.cream,
					quantity: 720,
					conversion: {
						requested: { amount: 720, unit: 'L' },
						buyerUnitsPerSalesUnit: 1,
						salesUnits: 720,
						lotSize: 6,
						rounded: false,
						method: 'COMPARISON_PRICE',
						crossCheck: 'AGREES'
					},
					offer: {
						unitPrice: 4.75,
						comparisonPrice: 4.75,
						comparisonUnit: 'L',
						logisticModel: 'STOCK',
						availableAmount: 900,
						availableDate: nextWeekday(6),
						closingTime: closingTimeBefore(nextWeekday(6)),
						priceValidTo: daysFromNow(3),
						fetchedAt: minutesAgo(60 * 26)
					},
					lineTotal: 3420,
					substitutesFor: null
				}
			],
			totals: totals(3420),
			policy: {
				outcome: 'REJECT',
				mandateVersion: 2,
				reasons: [
					{
						code: 'OVER_ORDER_LIMIT',
						severity: 'REJECT',
						message: 'The order total of €3,420 is over the €3,000 order limit.',
						facts: { orderTotal: 3420, maxOrderTotal: 3000 }
					}
				]
			},
			changes: [],
			statusHistory: [{ status: 'REJECTED', at: minutesAgo(60 * 26), by: 'system' }],
			createdAt: minutesAgo(60 * 26),
			checkAgainAfterSeconds: null,
			approverNote: null
		},
		{
			orderId: 'ORD-0125',
			quoteId: 'Q-0366',
			organisationId: 'org-merikoski',
			organisationName: 'Merikoski Hospital kitchen',
			agent: { id: 'agt-ward', name: 'ward-kitchen' },
			status: 'REJECTED',
			buyerRequest: 'Breakfast muesli for the cardiology ward.',
			rationale: 'Cheapest muesli in stock.',
			deliverBy: tuesday,
			lines: [
				{
					ref: 'L1',
					product: PRODUCTS.muesli,
					quantity: 6,
					conversion: null,
					offer: {
						unitPrice: 11.9,
						comparisonPrice: 4.76,
						comparisonUnit: 'KG',
						logisticModel: 'STOCK',
						availableAmount: 40,
						availableDate: tuesday,
						closingTime: closingTimeBefore(tuesday),
						priceValidTo: daysFromNow(3),
						fetchedAt: minutesAgo(60 * 30)
					},
					lineTotal: 71.4,
					substitutesFor: null
				}
			],
			totals: totals(71.4),
			policy: {
				outcome: 'REJECT',
				mandateVersion: 7,
				reasons: [
					{
						code: 'ALLERGEN_NOT_DECLARED_FREE',
						severity: 'REJECT',
						lineRef: 'L1',
						message:
							'The manufacturer has not declared this product free from milk or gluten cereals. Missing data counts as not free-from.',
						facts: { excluded: 'AM, AW', declared: 'none', source: 'missing' }
					}
				]
			},
			changes: [],
			statusHistory: [{ status: 'REJECTED', at: minutesAgo(60 * 30), by: 'system' }],
			createdAt: minutesAgo(60 * 30),
			checkAgainAfterSeconds: null,
			approverNote: null
		}
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
		productCode: '377815',
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
		productCode: '402115',
		productName: PRODUCTS.butterLf.name,
		kind: 'PRICE_CHANGE',
		detail: 'Price up 8% at the next re-check',
		active: false
	}
];
