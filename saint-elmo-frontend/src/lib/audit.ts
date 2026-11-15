import type { AuditEvent, AuditEventType } from '#lib/api/types.js';

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
} as const satisfies Record<AuditEventType, 'quote' | 'order' | 'agent' | null>;

/** Every event type the backend records, in the order an order's trail runs. */
export const AUDIT_EVENT_TYPES = Object.keys(SUBJECT) as AuditEventType[];

export const isAuditEventType = (type: string): type is AuditEventType =>
	Object.hasOwn(SUBJECT, type);

/** The order an event is about, if it is about one. */
export const orderOf = (e: AuditEvent) => (SUBJECT[e.type] === 'order' && e.subjectId) || undefined;

/** The agent an event is of: the one that acted, or the one it is about. */
export const agentOf = (e: AuditEvent) =>
	(e.actor.kind === 'agent' && e.actor.id) ||
	(SUBJECT[e.type] === 'agent' && e.subjectId) ||
	undefined;

/** A quote's request as recorded: what the buyer asked for, and the quote it revises. */
export function quoteRequest(e: AuditEvent) {
	const request = e.type === 'QUOTE_CREATED' ? e.payload.request : undefined;
	if (!request || typeof request !== 'object') return undefined;
	const { buyerRequest, previousQuoteId } = request as Record<string, unknown>;
	return {
		buyerRequest: typeof buyerRequest === 'string' ? buyerRequest : undefined,
		previousQuoteId: typeof previousQuoteId === 'string' ? previousQuoteId : undefined
	};
}
