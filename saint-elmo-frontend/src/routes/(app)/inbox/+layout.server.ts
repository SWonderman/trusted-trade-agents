import { api, apiModes } from '#lib/server/api/index.js';
import { requireCaller, requireRole } from '#lib/server/session.js';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals, url, depends }) => {
	const caller = requireCaller(locals, url);
	requireRole(caller, 'BUYER_ADMIN', 'APPROVER');
	depends('app:inbox');

	const all = await api.orders.list(caller);
	return {
		source: apiModes.orders,
		// One row per order for the table; the drawer loads the full order.
		orders: all.map((o) => ({
			orderId: o.orderId,
			agentName: o.agent.name,
			status: o.status,
			total: o.totals.net,
			createdAt: o.createdAt,
			buyerRequest: o.buyerRequest,
			topReason:
				o.policy.reasons.find((r) => r.severity === 'REJECT' || r.severity === 'NEEDS_HUMAN')
					?.code ?? null,
			moreReasons: Math.max(
				0,
				o.policy.reasons.filter((r) => r.severity === 'REJECT' || r.severity === 'NEEDS_HUMAN')
					.length - 1
			)
		}))
	};
};
