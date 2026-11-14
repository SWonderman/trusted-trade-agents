import { error, fail, redirect, type RequestEvent } from '@sveltejs/kit';
import { api } from '#lib/server/api/index.js';
import { attempt, text } from '#lib/server/actions.js';
import { requireCaller } from '#lib/server/session.js';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, url, params, depends }) => {
	const caller = requireCaller(locals, url);
	depends('app:inbox');
	const order = await api.orders.get(caller, params.orderId);
	if (!order) error(404, `There’s no order ${params.orderId} in your organisation.`);
	const agent = await api.agents.get(caller, order.agent.id);
	return { order, mandate: agent?.mandate ?? null, periodSpend: agent?.periodSpend ?? null };
};

async function decide(kind: 'approve' | 'reject', event: RequestEvent<{ orderId: string }>) {
	const caller = requireCaller(event.locals, event.url);
	const orderId = event.params.orderId;
	const note = text(await event.request.formData(), 'note') || undefined;

	if (kind === 'reject' && !note) {
		return fail(400, {
			action: kind,
			error: 'Add a note so the agent and the audit trail say why it was rejected.'
		});
	}

	const result = await attempt(() =>
		kind === 'approve'
			? api.orders.approve(caller, orderId, note)
			: api.orders.reject(caller, orderId, note)
	);
	if (!result.ok) return result.failure;

	// Move on to the oldest order still waiting, like working through a queue.
	const next = (await api.orders.list(caller, { status: 'PENDING_APPROVAL' })).at(-1);
	const done = `${result.value.orderId}:${result.value.status}`;
	redirect(303, next ? `/inbox/${next.orderId}?done=${done}` : `/inbox?done=${done}`);
}

export const actions: Actions = {
	approve: (event) => decide('approve', event),
	reject: (event) => decide('reject', event)
};
