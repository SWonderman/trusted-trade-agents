import type { Handle } from '@sveltejs/kit/hooks';
import { SESSION_COOKIE } from '#lib/server/session.js';
import { api } from '#lib/server/api/index.js';

/** Reads `exp` from a JWT without verifying it; FastAPI verifies every request. */
function expiresAt(token: string): number | null {
	try {
		const { exp } = JSON.parse(Buffer.from(token.split('.')[1], 'base64url').toString());
		return typeof exp === 'number' ? exp * 1000 : null;
	} catch {
		return null;
	}
}

export const handle: Handle = async ({ event, resolve }) => {
	event.locals.caller = null;
	const token = event.cookies.get(SESSION_COOKIE);

	if (token) {
		const exp = expiresAt(token);
		const user = exp && exp > Date.now() ? await api.auth.session(token) : null;
		if (user) {
			event.locals.caller = { token, user };
			event.locals.sessionExpiresAt = exp ?? undefined;
		} else {
			event.cookies.delete(SESSION_COOKIE, { path: '/' });
		}
	}

	// The signed-in console has its own theme; set it before first paint (see layout.css).
	const inConsole = event.route.id?.startsWith('/(app)');
	return resolve(event, {
		transformPageChunk: inConsole
			? ({ html }) => html.replace('<html lang="en"', '<html lang="en" class="console"')
			: undefined
	});
};
