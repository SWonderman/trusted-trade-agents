import { defineEnvVars } from '@sveltejs/kit/env';

const API_MODES = ['mock', 'http'] as const;
export type ApiMode = (typeof API_MODES)[number];

function apiMode(value: string | undefined): ApiMode | undefined {
	if (value === undefined || value === '') return undefined;
	if ((API_MODES as readonly string[]).includes(value)) return value as ApiMode;
	throw new Error(`expected one of ${API_MODES.join(', ')}, got "${value}"`);
}

export const variables = defineEnvVars({
	/** Where server-side data comes from: the in-memory mock or the FastAPI backend. */
	API_MODE: { schema: (value) => apiMode(value) ?? 'mock' },
	/** Per-namespace overrides, so real endpoints can be switched on one at a time. */
	API_MODE_AUTH: { schema: apiMode },
	API_MODE_ORDERS: { schema: apiMode },
	API_MODE_AGENTS: { schema: apiMode },
	API_MODE_AUDIT: { schema: apiMode },
	API_MODE_OVERSIGHT: { schema: apiMode },
	/** FastAPI base URL, reached only from SvelteKit's server side. */
	BACKEND_URL: { schema: (value) => value || 'http://localhost:8000' },
	/** Set to "false" only for plain-http local development without TLS. */
	SESSION_COOKIE_SECURE: { schema: (value) => value !== 'false' }
});
