import { fail } from '@sveltejs/kit';
import { ApiError } from './api';

/**
 * Runs an API call inside a form action and turns an ApiError into a form
 * failure the page can show, instead of an error page.
 */
export async function attempt<T>(fn: () => Promise<T>) {
	try {
		return { ok: true as const, value: await fn() };
	} catch (e) {
		if (e instanceof ApiError) {
			const status = e.status >= 400 && e.status < 600 ? e.status : 500;
			return {
				ok: false as const,
				failure: fail(status, { error: e.message, code: e.code })
			};
		}
		throw e;
	}
}

export function text(data: FormData, key: string) {
	const v = data.get(key);
	return typeof v === 'string' ? v.trim() : '';
}
