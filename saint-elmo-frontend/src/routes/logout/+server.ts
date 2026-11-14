import { redirect } from '@sveltejs/kit';
import { clearSession } from '#lib/server/session.js';
import type { RequestHandler } from './$types';

/** POST only, so a link or prefetch can't sign someone out. */
export const POST: RequestHandler = ({ cookies }) => {
	clearSession(cookies);
	redirect(303, '/login');
};
