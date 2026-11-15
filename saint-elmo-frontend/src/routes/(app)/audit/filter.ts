import type { AuditFilter, PolicyOutcome } from '#lib/api/types.js';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const OUTCOMES: PolicyOutcome[] = ['AUTO_APPROVE', 'NEEDS_HUMAN', 'REJECT'];

/** Filters live in the URL, so a filtered view can be linked and shared. */
export function readAuditFilter(url: URL): AuditFilter {
	const get = (k: string) => url.searchParams.get(k)?.trim() || undefined;
	const outcome = get('outcome');
	const order = get('order');
	return {
		agentId: get('agent'),
		// Mock ids read like ORD-0142; the backend's are UUIDs, written in lower case.
		orderId: order && (UUID.test(order) ? order.toLowerCase() : order.toUpperCase()),
		type: get('type'),
		outcome: OUTCOMES.includes(outcome as PolicyOutcome) ? (outcome as PolicyOutcome) : undefined
	};
}
