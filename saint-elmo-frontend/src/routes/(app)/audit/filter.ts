import type { AuditFilter } from '#lib/api/types.js';
import { isAuditEventType } from '#lib/audit.js';
import { isUuid } from '#lib/ids.js';

/** An ISO date-time, or nothing for a value that isn't a time. */
function isoInstant(value: string | undefined) {
	const t = value ? new Date(value) : null;
	return t && !Number.isNaN(t.getTime()) ? t.toISOString() : undefined;
}

/**
 * Filters live in the URL, so a filtered view can be linked and shared. The parameters
 * are the backend's own: agentId, type, subject, from (inclusive) and to (exclusive).
 */
export function readAuditFilter(url: URL): AuditFilter {
	const get = (k: string) => url.searchParams.get(k)?.trim() || undefined;
	const type = get('type');
	const subject = get('subject');
	return {
		agentId: get('agentId'),
		type: type && isAuditEventType(type) ? type : undefined,
		// Quote, order and agent ids are UUIDs, written in lower case.
		subject: subject && (isUuid(subject) ? subject.toLowerCase() : subject),
		from: isoInstant(get('from')),
		to: isoInstant(get('to'))
	};
}

export const isFiltered = (f: AuditFilter) => Object.values(f).some(Boolean);

/** Events per "load more" on the page; the export reads the backend's largest pages. */
export const PAGE_SIZE = 50;
export const EXPORT_PAGE_SIZE = 200;
