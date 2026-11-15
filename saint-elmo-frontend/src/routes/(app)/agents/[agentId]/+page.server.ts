import { error, fail } from '@sveltejs/kit';
import { MCP_URL } from '$app/env/private';
import { api } from '#lib/server/api/index.js';
import { attempt, text } from '#lib/server/actions.js';
import { requireCaller } from '#lib/server/session.js';
import type { KeyPreset } from '#lib/api/types.js';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, url, params, depends }) => {
	const caller = requireCaller(locals, url);
	depends('app:agents');
	const agent = await api.agents.get(caller, params.agentId);
	if (!agent) error(404, 'There’s no such agent in your organisation.');
	return {
		agent,
		keys: await api.agents.listKeys(caller, params.agentId),
		created: url.searchParams.has('created'),
		mcpUrl: MCP_URL
	};
};

export const actions: Actions = {
	issueKey: async ({ locals, url, params, request }) => {
		const caller = requireCaller(locals, url);
		const data = await request.formData();
		const label = text(data, 'label');
		const preset = text(data, 'preset') as KeyPreset;
		const expiresInDays = Number(text(data, 'expiresInDays'));
		if (!label)
			return fail(400, {
				action: 'issueKey',
				error: 'Name the token after where it will be used.'
			});
		if (preset !== 'PURCHASING' && preset !== 'RESEARCH_ONLY') {
			return fail(400, { action: 'issueKey', error: 'Choose what the token may do.' });
		}
		const r = await attempt(() =>
			api.agents.issueKey(caller, params.agentId, { label, preset, expiresInDays })
		);
		if (!r.ok) return r.failure;
		// The secret goes back to this one response only; it is never stored or shown again.
		return { action: 'issueKey', issued: r.value };
	},

	revokeKey: async ({ locals, url, params, request }) => {
		const caller = requireCaller(locals, url);
		const jti = text(await request.formData(), 'jti');
		const r = await attempt(() => api.agents.revokeKey(caller, params.agentId, jti));
		if (!r.ok) return r.failure;
		return { action: 'revokeKey', revoked: r.value.prefix };
	},

	setStatus: async ({ locals, url, params, request }) => {
		const caller = requireCaller(locals, url);
		const status = text(await request.formData(), 'status') === 'DISABLED' ? 'DISABLED' : 'ACTIVE';
		const r = await attempt(() => api.agents.setStatus(caller, params.agentId, status));
		if (!r.ok) return r.failure;
		return { action: 'setStatus' };
	}
};
