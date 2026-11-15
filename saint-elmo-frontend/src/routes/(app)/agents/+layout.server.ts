import { api, apiModes } from '#lib/server/api/index.js';
import { requireCaller, requireRole } from '#lib/server/session.js';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals, url, depends }) => {
	const caller = requireCaller(locals, url);
	requireRole(caller, 'BUYER_ADMIN');
	depends('app:agents');
	const [agents, waiting] = await Promise.all([
		api.agents.list(caller),
		api.orders.list(caller, { status: 'PENDING_APPROVAL' })
	]);
	// Orders waiting for a person, per agent, for the badge on each node
	const waitingByAgent: Record<string, number> = {};
	for (const o of waiting) waitingByAgent[o.agent.id] = (waitingByAgent[o.agent.id] ?? 0) + 1;
	return { agents, waitingByAgent, source: apiModes.agents };
};
