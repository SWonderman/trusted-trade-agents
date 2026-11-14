import { json } from '@sveltejs/kit';
import { api } from '#lib/server/api/index.js';
import { requireCaller } from '#lib/server/session.js';
import { readAuditFilter } from '../filter.js';
import type { RequestHandler } from './$types';

/** The same trail as the page, as JSON, for the buyer's own records or Valio Aimo's. */
export const GET: RequestHandler = async ({ locals, url }) => {
	const caller = requireCaller(locals, url);
	const filter = readAuditFilter(url);
	const events = await api.audit.list(caller, filter);
	return json(
		{ exportedAt: new Date().toISOString(), exportedBy: caller.user.email, filter, events },
		{
			headers: {
				'content-disposition': `attachment; filename="saint-elmo-audit-${new Date().toISOString().slice(0, 10)}.json"`
			}
		}
	);
};
