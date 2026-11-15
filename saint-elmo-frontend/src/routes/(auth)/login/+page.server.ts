import { fail, redirect } from '@sveltejs/kit';
import { api, apiModes, ApiError } from '#lib/server/api/index.js';
import { setSession } from '#lib/server/session.js';
import { text } from '#lib/server/actions.js';
import type { Actions, PageServerLoad } from './$types';

function safeNext(next: string | null) {
	// Only same-site paths, so the login page can't be used as an open redirect.
	return next && next.startsWith('/') && !next.startsWith('//') ? next : null;
}

const home = (role: string) => (role === 'AIMO_STAFF' ? '/oversight' : '/inbox');

export const load: PageServerLoad = async ({ locals, url }) => {
	if (locals.caller)
		redirect(303, safeNext(url.searchParams.get('next')) ?? home(locals.caller.user.role));
	return {
		demoAccounts: await api.auth.demoAccounts(),
		environment: apiModes.auth === 'http' ? ('live' as const) : ('mock' as const)
	};
};

export const actions: Actions = {
	default: async ({ request, cookies, url }) => {
		const data = await request.formData();
		const email = text(data, 'email');
		if (!email || !text(data, 'password')) {
			return fail(400, { email, error: 'Enter your work email and password.' });
		}
		try {
			const { token, user, expiresInSeconds } = await api.auth.login(
				email,
				String(data.get('password'))
			);
			setSession(cookies, token, expiresInSeconds);
			redirect(303, safeNext(url.searchParams.get('next')) ?? home(user.role));
		} catch (e) {
			if (e instanceof ApiError)
				return fail(e.status === 401 ? 400 : e.status, { email, error: e.message });
			throw e;
		}
	}
};
