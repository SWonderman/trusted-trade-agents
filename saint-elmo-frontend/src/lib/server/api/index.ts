import {
	API_MODE,
	API_MODE_AGENTS,
	API_MODE_AUDIT,
	API_MODE_AUTH,
	API_MODE_ORDERS,
	API_MODE_OVERSIGHT,
	BACKEND_URL
} from '$app/env/private';
import type { SaintElmoApi } from './client';
import { httpApi } from './http';
import { mockApi } from './mock';

export { ApiError, type Caller, type SaintElmoApi } from './client';

const http = httpApi(BACKEND_URL);
const pick = (mode: 'mock' | 'http' | undefined) =>
	(mode ?? API_MODE) === 'http' ? http : mockApi;

/**
 * The API the server side uses, assembled per namespace so real backend
 * endpoints can be switched on one at a time (API_MODE_ORDERS=http, …).
 */
export const api: SaintElmoApi = {
	auth: pick(API_MODE_AUTH).auth,
	orders: pick(API_MODE_ORDERS).orders,
	agents: pick(API_MODE_AGENTS).agents,
	audit: pick(API_MODE_AUDIT).audit,
	oversight: pick(API_MODE_OVERSIGHT).oversight
};

/** True when any namespace still answers from the mock; shown in the UI. */
export const usingMock = [
	API_MODE_AUTH,
	API_MODE_ORDERS,
	API_MODE_AGENTS,
	API_MODE_AUDIT,
	API_MODE_OVERSIGHT
].some((m) => (m ?? API_MODE) === 'mock');
