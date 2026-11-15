import type {
	AuditEvent,
	BackendAuditEvent,
	BackendAuditEventList,
	BackendAuditEventType,
	BackendOrderTrail
} from '#lib/api/types.js';
import { ApiError, type AuditApi, type Caller } from '../client';

/** The http client's GET, as much of it as the audit area needs. */
export type Get = <T>(
	path: string,
	init: { caller: Caller; query?: Record<string, string | undefined> }
) => Promise<T>;

/** What each event type is about, i.e. what its `subjectId` names. */
const SUBJECT = {
	QUOTE_CREATED: 'quote',
	SUBSTITUTES_REQUESTED: null,
	ORDER_REQUESTED: 'order',
	ORDER_RECHECKED: 'order',
	ORDER_CONFIRMED: 'order',
	ORDER_PENDING_APPROVAL: 'order',
	ORDER_APPROVED: 'order',
	ORDER_PLACED: 'order',
	ORDER_REJECTED: 'order',
	ORDER_REJECTED_BY_HUMAN: 'order',
	AGENT_TOKEN_ISSUED: 'agent',
	AGENT_TOKEN_REVOKED: 'agent',
	AGENT_DISABLED: 'agent'
} as const satisfies Record<BackendAuditEventType, 'quote' | 'order' | 'agent' | null>;

const isEventType = (type: string): type is BackendAuditEventType => Object.hasOwn(SUBJECT, type);

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** The backend pages at most 200 events; the page reads at most this many. */
const PAGE_SIZE = 200;
const MAX_EVENTS = 1000;

/** A backend audit event in the shape the timeline and the export use. */
export function toAuditEvent(e: BackendAuditEvent, caller: Caller): AuditEvent {
	const about = SUBJECT[e.type];
	const subject = e.subjectId ?? undefined;
	const quoteId = typeof e.payload.quoteId === 'string' ? e.payload.quoteId : undefined;
	return {
		id: e.id,
		at: e.at,
		// The backend answers for the caller's own organisation only.
		organisationId: caller.user.organisation?.id ?? '',
		organisationName: caller.user.organisation?.name ?? '',
		actor: { kind: e.actor.kind, name: e.actor.name },
		type: e.type,
		summary: e.summary,
		orderId: about === 'order' ? subject : undefined,
		quoteId: about === 'quote' ? subject : quoteId,
		agentId:
			e.actor.kind === 'agent' && e.actor.id ? e.actor.id : about === 'agent' ? subject : undefined,
		outcome: e.outcome ?? undefined,
		reasonCodes: e.reasonCodes ?? undefined,
		payload: e.payload
	};
}

/**
 * GET /api/v1/audit-events and GET /api/v1/orders/{id}/trail.
 *
 * An order filter reads the order's whole trail (its quotes, revisions and substitute
 * requests too), as the mock does; a quote id falls back to the events about that quote.
 * The backend filters by agent and event type itself; the policy outcome is filtered here.
 */
export function httpAudit(get: Get): AuditApi {
	async function listAll(
		caller: Caller,
		query: Record<string, string | undefined>
	): Promise<BackendAuditEvent[]> {
		const items: BackendAuditEvent[] = [];
		let cursor: string | undefined;
		do {
			const page = await get<BackendAuditEventList>('/api/v1/audit-events', {
				caller,
				query: { ...query, limit: String(PAGE_SIZE), cursor }
			});
			items.push(...page.items);
			cursor = page.nextCursor ?? undefined;
		} while (cursor && items.length < MAX_EVENTS);
		return items;
	}

	async function orderTrail(caller: Caller, orderId: string) {
		try {
			const trail = await get<BackendOrderTrail>(
				`/api/v1/orders/${encodeURIComponent(orderId)}/trail`,
				{ caller }
			);
			return trail.items.toReversed(); // oldest first → newest first, like the list
		} catch (e) {
			if (e instanceof ApiError && e.status === 404) return null;
			throw e;
		}
	}

	return {
		async list(caller, filter) {
			// The backend refuses ids and types it does not know; they simply match nothing here.
			if (filter.type && !isEventType(filter.type)) return [];
			if (filter.orderId && !UUID.test(filter.orderId)) return [];

			const query = { agentId: filter.agentId, type: filter.type };
			const trail = filter.orderId ? await orderTrail(caller, filter.orderId) : null;
			const events = trail
				? trail.filter(
						(e) =>
							(!filter.type || e.type === filter.type) &&
							(!filter.agentId ||
								e.actor.id === filter.agentId ||
								(SUBJECT[e.type] === 'agent' && e.subjectId === filter.agentId))
					)
				: await listAll(caller, { ...query, subject: filter.orderId });

			return events
				.filter((e) => !filter.outcome || e.outcome === filter.outcome)
				.map((e) => toAuditEvent(e, caller));
		}
	};
}
