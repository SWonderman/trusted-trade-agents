import { api, apiModes } from '#lib/server/api/index.js';
import { requireCaller } from '#lib/server/session.js';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals, url, depends }) => {
	const caller = requireCaller(locals, url);
	depends('app:inbox');

	const pending =
		caller.user.role === 'AIMO_STAFF'
			? 0
			: (await api.orders.list(caller, { status: 'PENDING_APPROVAL' })).length;

	return {
		user: caller.user,
		pending,
		modes: apiModes,
		sessionExpiresAt: locals.sessionExpiresAt ?? null,
		checkedAt: new Date().toISOString()
	};
};
