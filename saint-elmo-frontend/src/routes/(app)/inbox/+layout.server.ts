import { api, apiModes } from '#lib/server/api/index.js';
import { requireCaller, requireRole } from '#lib/server/session.js';
import type { Order } from '#lib/api/types.js';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals, url, depends }) => {
	const caller = requireCaller(locals, url);
	requireRole(caller, 'BUYER_ADMIN', 'APPROVER');
	depends('app:inbox');

	// Every order waiting for a person, however old, plus the most recent of the rest.
	const [waiting, recent] = await Promise.all([
		api.orders.list(caller, { status: 'PENDING_APPROVAL' }),
		api.orders.list(caller)
	]);
	const all = [...new Map([...recent, ...waiting].map((o) => [o.orderId, o])).values()].sort(
		(a, b) => b.createdAt.localeCompare(a.createdAt)
	);
	const held = (o: Order) =>
		o.policy.reasons.filter((r) => r.severity === 'REJECT' || r.severity === 'NEEDS_HUMAN');

	return {
		source: apiModes.orders,
		// One row per order for the table; the modal loads the full order.
		orders: all.map((o) => ({
			orderId: o.orderId,
			agentName: o.agent.name,
			status: o.status,
			total: o.totals.net,
			createdAt: o.createdAt,
			buyerRequest: o.buyerRequest,
			topReason: held(o)[0]?.code ?? null,
			moreReasons: Math.max(0, held(o).length - 1)
		}))
	};
};
