import { fail } from '@sveltejs/kit';
import { ApiError } from './api';

/**
 * Runs an API call inside a form action and turns an ApiError into a form
 * failure the page can show, instead of an error page. `messages` replaces the
 * backend's message for the error codes a page can explain better.
 */
export async function attempt<T>(fn: () => Promise<T>, messages: Record<string, string> = {}) {
	try {
		return { ok: true as const, value: await fn() };
	} catch (e) {
		if (e instanceof ApiError) {
			const status = e.status >= 400 && e.status < 600 ? e.status : 500;
			return {
				ok: false as const,
				failure: fail(status, { error: messages[e.code] ?? e.message, code: e.code })
			};
		}
		throw e;
	}
}

export function text(data: FormData, key: string) {
	const v = data.get(key);
	return typeof v === 'string' ? v.trim() : '';
}
