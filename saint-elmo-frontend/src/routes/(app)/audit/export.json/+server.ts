import { json } from '@sveltejs/kit';
import type { AuditEvent } from '#lib/api/types.js';
import { api } from '#lib/server/api/index.js';
import { requireCaller } from '#lib/server/session.js';
import { EXPORT_PAGE_SIZE, readAuditFilter } from '../filter.js';
import type { RequestHandler } from './$types';

/**
 * Every event matching the page's filter, all pages, as JSON: how a buyer shares their
 * trail with Valio Aimo. Each event carries its summary and its recorded payload.
 */
export const GET: RequestHandler = async ({ locals, url }) => {
	const caller = requireCaller(locals, url);
	const filter = readAuditFilter(url);
	const events: AuditEvent[] = [];
	let cursor: string | undefined;
	do {
		const page = await api.audit.list(caller, filter, { cursor, limit: EXPORT_PAGE_SIZE });
		events.push(...page.items);
		cursor = page.nextCursor ?? undefined;
	} while (cursor);
	return json(
		{ exportedAt: new Date().toISOString(), exportedBy: caller.user.email, filter, events },
		{
			headers: {
				'content-disposition': `attachment; filename="saint-elmo-audit-${new Date().toISOString().slice(0, 10)}.json"`
			}
		}
	);
};
