// See https://svelte.dev/docs/kit/types#app.d.ts
import type { Caller } from '#lib/server/api/index.js';

declare global {
	namespace App {
		interface Locals {
			/** Set by hooks.server.ts from the session cookie; null when signed out. */
			caller: Caller | null;
			sessionExpiresAt?: number;
		}
		interface Error {
			message: string;
			code?: string;
		}
	}
}

export {};
