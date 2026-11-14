import { api, apiModes } from '#lib/server/api/index.js';
import { requireCaller, requireRole } from '#lib/server/session.js';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals, url, depends }) => {
	const caller = requireCaller(locals, url);
	requireRole(caller, 'BUYER_ADMIN', 'APPROVER');
	depends('app:inbox');

	const all = await api.orders.list(caller);
	const summarise = (o: (typeof all)[number]) => ({
		orderId: o.orderId,
		agentName: o.agent.name,
		status: o.status,
		total: o.totals.net,
		createdAt: o.createdAt,
		buyerRequest: o.buyerRequest,
		reasonCount: o.policy.reasons.filter((r) => r.severity !== 'INFO').length,
		topReason:
			o.policy.reasons.find((r) => r.severity === 'NEEDS_HUMAN' || r.severity === 'REJECT')?.code ??
			null,
		hasSubstitute: o.lines.some((l) => l.substitutesFor)
	});

	return {
		source: apiModes.orders,
		pending: all.filter((o) => o.status === 'PENDING_APPROVAL').map(summarise),
		recent: all
			.filter((o) => o.status !== 'PENDING_APPROVAL')
			.slice(0, 4)
			.map(summarise)
	};
};
