import { error, fail, redirect, type RequestEvent } from '@sveltejs/kit';
import { api, ApiError, type Caller } from '#lib/server/api/index.js';
import { attempt, text } from '#lib/server/actions.js';
import { requireCaller } from '#lib/server/session.js';
import type { Order, ProductFacts } from '#lib/api/types.js';
import type { Actions, PageServerLoad } from './$types';

/**
 * Context around the order, which stands on its own: when the API can't give it (an
 * agent the mock doesn't know, a product missing from the catalog, a role that can't
 * read agents), the page leaves it out. Anything but an API error still fails the page.
 */
async function context<T>(p: Promise<T | null>): Promise<T | null> {
	try {
		return await p;
	} catch (e) {
		if (e instanceof ApiError) return null;
		throw e;
	}
}

/** The catalog's facts for each product on the order, and each product a line substitutes. */
async function productFacts(caller: Caller, order: Order) {
	const codes = new Set(order.lines.flatMap((l) => [l.productCode, l.substitutesFor ?? []].flat()));
	const found = await Promise.all(
		[...codes].map((code) => context(api.catalog.product(caller, code)))
	);
	const facts: Record<string, ProductFacts> = {};
	for (const p of found) {
		if (p) {
			facts[p.code] = {
				name: p.name,
				vendor: p.vendor,
				claims: p.claims,
				diets: p.diets,
				labels: p.labels
			};
		}
	}
	return facts;
}

export const load: PageServerLoad = async ({ locals, url, params, depends }) => {
	const caller = requireCaller(locals, url);
	depends('app:inbox');
	const order = await api.orders.get(caller, params.orderId);
	if (!order) error(404, `There’s no order ${params.orderId} in your organisation.`);
	const [agent, products, trail] = await Promise.all([
		// Agents may still answer from the mock (#22), which doesn't know the backend's ids.
		context(api.agents.get(caller, order.agent.id)),
		productFacts(caller, order),
		// Oldest first: the buyer's request, quotes and substitutes, then the order's own steps.
		context(api.audit.orderTrail(caller, order.orderId))
	]);
	return {
		order,
		products,
		trail: trail ?? [],
		mandate: agent?.mandate ?? null,
		periodSpend: agent?.periodSpend ?? null
	};
};

/** What the page says when a decision can't be made, by the backend's error code. */
const REFUSED: Record<string, string> = {
	ORDER_NOT_PENDING:
		'This order was decided before you got to it, by another approver or by its agent. Here it is as it stands now.',
	ORDER_NOT_FOUND: 'There’s no such order in your organisation.',
	PERMISSION_DENIED:
		'Your account can’t approve or reject orders. A buyer admin or an approver has to decide this one.',
	// Approving re-checks live data first; when that can't run, nothing is decided.
	VALIO_AIMO_UNAVAILABLE:
		'Approving re-checks live price and stock, and Valio Aimo’s API isn’t answering. Nothing was decided; try again in a minute.',
	MANDATE_NOT_FOUND:
		'The agent has no mandate to re-check this order against any more. Nothing was decided; reject it, or give the agent a mandate first.',
	PRODUCT_NOT_FOUND:
		'A product on this order is no longer in the catalog, so it can’t be re-checked. Nothing was decided; reject it.',
	CUSTOMER_NUMBER_MISSING:
		'Your organisation has no Valio Aimo customer number, so the order can’t be priced again. Nothing was decided.'
};

async function decide(kind: 'approve' | 'reject', event: RequestEvent<{ orderId: string }>) {
	const caller = requireCaller(event.locals, event.url);
	const orderId = event.params.orderId;
	const note = text(await event.request.formData(), 'note') || undefined;

	// The backend accepts a rejection without a note; the audit trail is better with one.
	if (kind === 'reject' && !note) {
		return fail(400, {
			action: kind,
			error: 'Add a note so the agent and the audit trail say why it was rejected.'
		});
	}

	const result = await attempt(
		() =>
			kind === 'approve'
				? api.orders.approve(caller, orderId, note)
				: api.orders.reject(caller, orderId, note),
		REFUSED
	);
	if (!result.ok) return result.failure;
	const order = result.value;

	// Approving re-checks live data: the order may come back rejected by a hard rule that
	// now applies, or still pending with something the approver hasn't seen. Stay on it.
	if (kind === 'approve' && order.status !== 'PLACED') {
		return {
			action: kind,
			recheck: {
				status: order.status,
				// Rejected: the hard rules that failed; still pending: what needs a person now
				reasonCodes: order.policy.reasons
					.filter((r) => r.severity === (order.status === 'REJECTED' ? 'REJECT' : 'NEEDS_HUMAN'))
					.map((r) => r.code),
				total: order.totals.net
			}
		};
	}

	// Move on to the oldest order still waiting, like working through a queue.
	const next = (await api.orders.list(caller, { status: 'PENDING_APPROVAL' })).at(-1);
	const done = `${order.orderId}:${order.status}`;
	redirect(303, next ? `/inbox/${next.orderId}?done=${done}` : `/inbox?done=${done}`);
}

export const actions: Actions = {
	approve: (event) => decide('approve', event),
	reject: (event) => decide('reject', event)
};
