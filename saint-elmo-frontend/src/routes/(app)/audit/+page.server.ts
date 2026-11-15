import { api, apiModes, ApiError } from '#lib/server/api/index.js';
import { requireCaller } from '#lib/server/session.js';
import { AUDIT_EVENT_TYPES } from '#lib/audit.js';
import { PAGE_SIZE, readAuditFilter } from './filter.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, url }) => {
	const caller = requireCaller(locals, url);
	const filter = readAuditFilter(url);
	const [page, agents] = await Promise.all([
		api.audit.list(caller, filter, { limit: PAGE_SIZE }),
		// Only agents from the same source as the trail share its ids: with agents still on the
		// mock (#22) and the trail live, the mock's ids would match nothing. Valio Aimo staff,
		// and roles that can't read agents, get none here.
		apiModes.agents === apiModes.audit
			? api.agents.list(caller).catch((e) => {
					if (e instanceof ApiError) return [];
					throw e;
				})
			: []
	]);

	// Plus every agent that acted in the events shown, so the trail's own agents can be picked.
	const options = new Map(agents.map((a) => [a.id, a.name]));
	for (const e of page.items) {
		if (e.actor.kind === 'agent' && e.actor.id) options.set(e.actor.id, e.actor.name);
	}

	return {
		source: apiModes.audit,
		page,
		filter,
		agentOptions: [...options]
			.map(([id, name]) => ({ id, name }))
			.sort((a, b) => a.name.localeCompare(b.name)),
		typeOptions: AUDIT_EVENT_TYPES,
		crossCustomer: caller.user.role === 'AIMO_STAFF'
	};
};
