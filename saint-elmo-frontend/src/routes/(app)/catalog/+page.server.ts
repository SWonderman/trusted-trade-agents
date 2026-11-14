import { api, apiModes, ApiError } from '#lib/server/api/index.js';
import { requireCaller } from '#lib/server/session.js';
import type { AllergenStrictness, ProductSearchRequest } from '#lib/api/types.js';
import type { PageServerLoad } from './$types';

const PAGE_SIZE = 25;
const STRICTNESS: AllergenStrictness[] = ['contains', 'may_contain', 'declared_free'];

/** Search and filters live in the URL, so a search can be linked and shared. */
function readSearch(url: URL) {
	const p = url.searchParams;
	const strictness = p.get('strictness') as AllergenStrictness | null;
	return {
		q: p.get('q')?.trim() ?? '',
		category: p.get('category') ?? '',
		claims: p.getAll('claim'), // "FREE_FROM:LACTOSE"
		allergens: p.getAll('allergen'), // "AM"
		strictness: strictness && STRICTNESS.includes(strictness) ? strictness : 'contains',
		page: Math.max(1, Number(p.get('page')) || 1)
	};
}

export const load: PageServerLoad = async ({ locals, url }) => {
	const caller = requireCaller(locals, url);
	const search = readSearch(url);

	const request: ProductSearchRequest = {
		query: search.q || null,
		language: 'en',
		categoryCodes: search.category ? [search.category] : [],
		requiredClaims: search.claims.map((c) => {
			const [type, element] = c.split(':');
			return { type, element };
		}),
		excludedAllergens: search.allergens,
		allergenStrictness: search.strictness,
		limit: PAGE_SIZE,
		offset: (search.page - 1) * PAGE_SIZE
	};

	try {
		const [vocabulary, results] = await Promise.all([
			api.catalog.vocabulary(caller),
			api.catalog.search(caller, request)
		]);
		return {
			source: apiModes.catalog,
			search,
			pageSize: PAGE_SIZE,
			vocabulary,
			results,
			error: null
		};
	} catch (e) {
		if (!(e instanceof ApiError)) throw e;
		return {
			source: apiModes.catalog,
			search,
			pageSize: PAGE_SIZE,
			vocabulary: null,
			results: null,
			error: { code: e.code, message: e.message }
		};
	}
};
