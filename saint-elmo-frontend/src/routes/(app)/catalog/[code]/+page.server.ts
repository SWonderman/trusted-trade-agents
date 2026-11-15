import { error } from '@sveltejs/kit';
import { api, apiModes } from '#lib/server/api/index.js';
import { requireCaller } from '#lib/server/session.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, url, params }) => {
	const caller = requireCaller(locals, url);
	const product = await api.catalog.product(caller, params.code);
	if (!product) error(404, `There’s no product ${params.code} in the catalog.`);
	return { product, source: apiModes.catalog };
};
