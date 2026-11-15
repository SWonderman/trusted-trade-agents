import type {
	ProductDetail,
	ProductHit,
	ProductRef,
	ProductSearchResponse,
	Vocabulary
} from '#lib/api/types.js';
import type { CatalogApi } from '../client';
import { PRODUCTS } from './fixtures';

/**
 * A small stand-in for the catalog, built from the products the demo orders use, so
 * the catalog page works in mock mode. The real catalog (17.5k products) needs
 * API_MODE_CATALOG=http.
 */

const provenance = { source: 'Demo fixtures', catalogSnapshotDate: '2026-11-13' };

function summary(p: ProductRef) {
	return {
		code: p.code,
		name: p.name,
		gtin: null,
		categoryCode: p.categoryCode ?? '',
		vendor: p.vendor ?? '',
		brand: null,
		salesUnit: p.salesUnit,
		baseUnit: p.salesUnit,
		allowedLotSize: 1,
		units: [{ code: p.salesUnit, sizeInBaseUnits: 1, gtin: null }],
		variableUnit: false,
		hasDeposit: false,
		claims: p.claims,
		diets: [],
		labels: p.labels,
		countryOfOrigin: 'fi',
		deliveryReliability: p.deliveryReliability,
		carbonFootprint: p.carbonFootprint
	};
}

function hit(p: ProductRef): ProductHit {
	return { ...summary(p), relevance: null, allergens: [] };
}

function detail(p: ProductRef): ProductDetail {
	return {
		...summary(p),
		allergens: [],
		translations: [],
		nutrients: [],
		ingredients: [],
		packagingLevels: [],
		deposits: [],
		producers: [],
		fishSpecies: [],
		safetySheets: [],
		curatedSubstitutes: [],
		provenance
	};
}

const products = Object.values(PRODUCTS) as ProductRef[];

export const mockCatalog: CatalogApi = {
	async search(_caller, request) {
		const q = request.query?.trim().toLowerCase();
		const categories = request.categoryCodes ?? [];
		const claims = request.requiredClaims ?? [];
		const matches = products.filter(
			(p) =>
				(!q || p.name.toLowerCase().includes(q) || p.code === q) &&
				(!categories.length || categories.includes(p.categoryCode ?? '')) &&
				claims.every((c) => p.claims.some((x) => x.type === c.type && x.element === c.element))
		);
		const offset = request.offset ?? 0;
		const limit = request.limit ?? 20;
		return {
			total: matches.length,
			items: matches.slice(offset, offset + limit).map(hit),
			provenance
		} satisfies ProductSearchResponse;
	},
	async product(_caller, code) {
		const p = products.find((x) => x.code === code);
		return p ? detail(p) : null;
	},
	async vocabulary() {
		const count = <T>(xs: T[], key: (x: T) => string) => {
			const m = new Map<string, number>();
			for (const x of xs) m.set(key(x), (m.get(key(x)) ?? 0) + 1);
			return m;
		};
		const claims = count(
			products.flatMap((p) => p.claims),
			(c) => `${c.type}:${c.element}`
		);
		return {
			claims: [...claims].map(([k, productCount]) => {
				const [type, element] = k.split(':');
				return {
					type: { code: type, name: null, definition: null },
					element: { code: element, name: null, definition: null },
					productCount
				};
			}),
			diets: [],
			labels: [],
			allergens: [],
			categories: [...count(products, (p) => p.categoryCode ?? '')].map(([code, productCount]) => ({
				code,
				productCount
			}))
		} satisfies Vocabulary;
	}
};
