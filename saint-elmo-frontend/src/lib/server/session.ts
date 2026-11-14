import { error, redirect, type Cookies } from '@sveltejs/kit';
import { SESSION_COOKIE_SECURE } from '$app/env/private';
import type { Role } from '#lib/api/types.js';
import type { Caller } from './api';

export const SESSION_COOKIE = 'se_session';

/** design.md §3.4: httpOnly, Secure, SameSite=Lax, Path=/. */
export function setSession(cookies: Cookies, token: string, maxAgeSeconds = 60 * 60) {
	cookies.set(SESSION_COOKIE, token, {
		path: '/',
		httpOnly: true,
		secure: SESSION_COOKIE_SECURE,
		sameSite: 'lax',
		maxAge: maxAgeSeconds
	});
}

export function clearSession(cookies: Cookies) {
	cookies.delete(SESSION_COOKIE, { path: '/' });
}

/** The signed-in caller, or a redirect to /login that returns here afterwards. */
export function requireCaller(locals: App.Locals, url: URL): Caller {
	if (!locals.caller) {
		redirect(303, `/login?next=${encodeURIComponent(url.pathname + url.search)}`);
	}
	return locals.caller;
}

export function requireRole(caller: Caller, ...roles: Role[]) {
	if (!roles.includes(caller.user.role)) {
		error(403, 'Your role can’t open this page.');
	}
}
