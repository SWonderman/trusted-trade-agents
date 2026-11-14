import { api } from '#lib/server/api/index.js';
import { requireCaller } from '#lib/server/session.js';
import { readAuditFilter } from './filter.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, url }) => {
	const caller = requireCaller(locals, url);
	const filter = readAuditFilter(url);
	const events = await api.audit.list(caller, filter);

	// Filter options come from the full visible trail, so a filter never hides its own choices.
	const all =
		filter.agentId || filter.orderId || filter.type || filter.outcome
			? await api.audit.list(caller, {})
			: events;
	const agents = new Map<string, string>();
	const types = new Set<string>();
	for (const e of all) {
		if (e.agentId && e.actor.kind === 'agent') agents.set(e.agentId, e.actor.name);
		types.add(e.tool ?? e.type);
	}

	return {
		events,
		filter,
		total: all.length,
		agentOptions: [...agents]
			.map(([id, name]) => ({ id, name }))
			.sort((a, b) => a.name.localeCompare(b.name)),
		typeOptions: [...types].sort(),
		crossCustomer: caller.user.role === 'aimo_staff'
	};
};
