import type { AuditEventPage, OrderTrail } from '#lib/api/types.js';
import { isUuid } from '#lib/ids.js';
import { ApiError, type AuditApi, type Caller } from '../client';

/** The http client's GET, as much of it as the audit area needs. */
export type Get = <T>(
	path: string,
	init: { caller: Caller; query?: Record<string, string | undefined> }
) => Promise<T>;

const EMPTY_PAGE: AuditEventPage = { items: [], nextCursor: null };

/** GET /api/v1/audit-events and GET /api/v1/orders/{id}/trail, as they are. */
export function httpAudit(get: Get): AuditApi {
	return {
		async list(caller, filter, page = {}) {
			// The backend refuses ids that aren't UUIDs; they simply match nothing here.
			if (filter.agentId && !isUuid(filter.agentId)) return EMPTY_PAGE;
			if (filter.subject && !isUuid(filter.subject)) return EMPTY_PAGE;
			return get<AuditEventPage>('/api/v1/audit-events', {
				caller,
				query: {
					...filter,
					cursor: page.cursor,
					limit: page.limit === undefined ? undefined : String(page.limit)
				}
			});
		},

		async orderTrail(caller, orderId) {
			if (!isUuid(orderId)) return null;
			try {
				const trail = await get<OrderTrail>(`/api/v1/orders/${encodeURIComponent(orderId)}/trail`, {
					caller
				});
				return trail.items;
			} catch (e) {
				if (e instanceof ApiError && e.status === 404) return null;
				throw e;
			}
		}
	};
}
