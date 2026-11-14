import { api, usingMock } from '#lib/server/api/index.js';
import { requireCaller } from '#lib/server/session.js';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals, url, depends }) => {
	const caller = requireCaller(locals, url);
	depends('app:inbox');

	const pending =
		caller.user.role === 'aimo_staff'
			? 0
			: (await api.orders.list(caller, { status: 'PENDING_APPROVAL' })).length;

	return {
		user: caller.user,
		pending,
		environment: usingMock ? ('mock' as const) : ('live' as const),
		sessionExpiresAt: locals.sessionExpiresAt ?? null,
		checkedAt: new Date().toISOString()
	};
};
