import {
	API_MODE,
	API_MODE_AGENTS,
	API_MODE_AUDIT,
	API_MODE_AUTH,
	API_MODE_CATALOG,
	API_MODE_ORDERS,
	API_MODE_OVERSIGHT,
	BACKEND_URL
} from '$app/env/private';
import type { SaintElmoApi } from './client';
import { httpApi } from './http';
import { mockApi } from './mock';

export { ApiError, type Caller, type SaintElmoApi } from './client';

type Area = keyof SaintElmoApi;
type Mode = 'mock' | 'http';

/** Where each area's data comes from: the backend, or the in-memory demo data. */
export const apiModes: Record<Area, Mode> = {
	auth: API_MODE_AUTH ?? API_MODE,
	catalog: API_MODE_CATALOG ?? API_MODE,
	orders: API_MODE_ORDERS ?? API_MODE,
	agents: API_MODE_AGENTS ?? API_MODE,
	audit: API_MODE_AUDIT ?? API_MODE,
	oversight: API_MODE_OVERSIGHT ?? API_MODE
};

// The backend only accepts its own session tokens, which only real sign-in issues.
if (apiModes.auth === 'mock') {
	const live = (Object.keys(apiModes) as Area[]).filter((a) => apiModes[a] === 'http');
	if (live.length) {
		throw new Error(
			`API_MODE_AUTH must be "http" when ${live.join(', ')} use the backend: ` +
				'the backend only accepts sessions it signed itself.'
		);
	}
}

const http = httpApi(BACKEND_URL);
const pick = (area: Area) => (apiModes[area] === 'http' ? http : mockApi)[area];

/**
 * The API the server side uses, assembled per area so real backend endpoints can be
 * switched on one at a time (API_MODE_CATALOG=http, …).
 */
export const api = {
	auth: pick('auth'),
	catalog: pick('catalog'),
	orders: pick('orders'),
	agents: pick('agents'),
	audit: pick('audit'),
	oversight: pick('oversight')
} as SaintElmoApi;

/** True when any area still answers from the mock; shown in the UI. */
export const usingMock = Object.values(apiModes).includes('mock');
