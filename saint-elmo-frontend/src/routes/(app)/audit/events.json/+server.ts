import { json } from '@sveltejs/kit';
import { api } from '#lib/server/api/index.js';
import { requireCaller } from '#lib/server/session.js';
import { PAGE_SIZE, readAuditFilter } from '../filter.js';
import type { RequestHandler } from './$types';

/** The next, older page of the trail the page shows, for "load more". */
export const GET: RequestHandler = async ({ locals, url }) => {
	const caller = requireCaller(locals, url);
	const cursor = url.searchParams.get('cursor') ?? undefined;
	return json(await api.audit.list(caller, readAuditFilter(url), { cursor, limit: PAGE_SIZE }));
};
