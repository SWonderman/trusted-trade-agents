import type { AuditFilter, PolicyOutcome } from '#lib/api/types.js';

const OUTCOMES: PolicyOutcome[] = ['AUTO_APPROVE', 'NEEDS_HUMAN', 'REJECT'];

/** Filters live in the URL, so a filtered view can be linked and shared. */
export function readAuditFilter(url: URL): AuditFilter {
	const get = (k: string) => url.searchParams.get(k)?.trim() || undefined;
	const outcome = get('outcome');
	return {
		agentId: get('agent'),
		orderId: get('order')?.toUpperCase(),
		type: get('type'),
		outcome: OUTCOMES.includes(outcome as PolicyOutcome) ? (outcome as PolicyOutcome) : undefined
	};
}
