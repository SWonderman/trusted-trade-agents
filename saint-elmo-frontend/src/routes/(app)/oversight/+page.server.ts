import { fail } from '@sveltejs/kit';
import { api, apiModes } from '#lib/server/api/index.js';
import { attempt, text } from '#lib/server/actions.js';
import { requireCaller, requireRole } from '#lib/server/session.js';
import type { ScenarioKind } from '#lib/api/types.js';
import type { Actions, PageServerLoad } from './$types';

const KINDS: ScenarioKind[] = ['OUT_OF_STOCK', 'PARTIAL', 'LATE', 'PRICE_CHANGE'];

export const load: PageServerLoad = async ({ locals, url, depends }) => {
	const caller = requireCaller(locals, url);
	requireRole(caller, 'AIMO_STAFF');
	depends('app:inbox');

	const [feed, scenarios] = await Promise.all([
		api.oversight.feed(caller),
		api.oversight.scenarios(caller)
	]);
	const since = Date.now() - 24 * 3600_000;
	const today = feed.filter((e) => new Date(e.at).getTime() > since);

	return {
		source: apiModes.oversight,
		feed,
		scenarios,
		stats: {
			organisations: new Set(feed.map((e) => e.organisationId)).size,
			quotes: today.filter((e) => e.type === 'QUOTE_CREATED').length,
			ordersPlaced: today.filter((e) => e.type === 'ORDER_PLACED').length,
			waiting: today.filter((e) => e.type === 'ORDER_PENDING_APPROVAL').length,
			rejected: today.filter((e) => e.type === 'ORDER_REJECTED').length
		},
		organisations: [...new Map(feed.map((e) => [e.organisationId, e.organisationName]))].map(
			([id, name]) => ({
				id,
				name
			})
		)
	};
};

export const actions: Actions = {
	toggle: async ({ locals, url, request }) => {
		const caller = requireCaller(locals, url);
		const data = await request.formData();
		const r = await attempt(() =>
			api.oversight.setScenario(caller, text(data, 'id'), text(data, 'active') === 'true')
		);
		return r.ok ? { action: 'toggle' } : r.failure;
	},

	add: async ({ locals, url, request }) => {
		const caller = requireCaller(locals, url);
		const data = await request.formData();
		const productCode = text(data, 'productCode');
		const kind = text(data, 'kind') as ScenarioKind;
		const detail = text(data, 'detail');
		if (!/^\d{4,8}$/.test(productCode))
			return fail(400, { action: 'add', error: 'Enter a product code, e.g. 463038.' });
		if (!KINDS.includes(kind))
			return fail(400, { action: 'add', error: 'Choose what should happen.' });
		const r = await attempt(() =>
			api.oversight.addScenario(caller, { productCode, kind, detail: detail || kind })
		);
		return r.ok ? { action: 'add' } : r.failure;
	},

	simulate: async ({ locals, url, request }) => {
		const caller = requireCaller(locals, url);
		const organisationId = text(await request.formData(), 'organisationId');
		const r = await attempt(() => api.oversight.simulateAgentOrder(caller, organisationId));
		return r.ok
			? { action: 'simulate', orderId: r.value.orderId, organisation: r.value.organisationName }
			: r.failure;
	}
};
