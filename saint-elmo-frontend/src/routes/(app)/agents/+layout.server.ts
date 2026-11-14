import { api, apiModes } from '#lib/server/api/index.js';
import { requireCaller, requireRole } from '#lib/server/session.js';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals, url, depends }) => {
	const caller = requireCaller(locals, url);
	requireRole(caller, 'BUYER_ADMIN');
	depends('app:agents');
	return { agents: await api.agents.list(caller), source: apiModes.agents };
};
