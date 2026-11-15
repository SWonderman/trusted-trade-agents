import type { AuditFilter, PolicyOutcome } from '#lib/api/types.js';
import { isUuid } from '#lib/ids.js';
const OUTCOMES: PolicyOutcome[] = ['AUTO_APPROVE', 'NEEDS_HUMAN', 'REJECT'];

/** Filters live in the URL, so a filtered view can be linked and shared. */
export function readAuditFilter(url: URL): AuditFilter {
	const get = (k: string) => url.searchParams.get(k)?.trim() || undefined;
	const outcome = get('outcome');
	const order = get('order');
	return {
		agentId: get('agent'),
		// Order and quote ids are UUIDs, written in lower case.
		orderId: order && (isUuid(order) ? order.toLowerCase() : order),
		type: get('type'),
		outcome: OUTCOMES.includes(outcome as PolicyOutcome) ? (outcome as PolicyOutcome) : undefined
	};
}
