import { fail, redirect } from '@sveltejs/kit';
import { api, ApiError } from '#lib/server/api/index.js';
import { attempt, text } from '#lib/server/actions.js';
import { requireCaller } from '#lib/server/session.js';
import type { AllergenStrictness, Mandate, SubstitutionPolicy } from '#lib/api/types.js';
import type { Actions, PageServerLoad } from './$types';

const money = (v: string) => (v === '' ? NaN : Number(v));
const codes = (v: string) =>
	v
		.split(/[\s,]+/)
		.map((s) => s.trim())
		.filter(Boolean);

/** The category codes products actually use, for the picker; null falls back to free text. */
export const load: PageServerLoad = async ({ locals, url }) => {
	const caller = requireCaller(locals, url);
	try {
		const { categories } = await api.catalog.vocabulary(caller);
		return { categories };
	} catch (e) {
		if (e instanceof ApiError) return { categories: null };
		throw e;
	}
};

export const actions: Actions = {
	default: async ({ locals, url, request }) => {
		const caller = requireCaller(locals, url);
		const data = await request.formData();
		const name = text(data, 'name').toLowerCase();
		const values = Object.fromEntries(
			[...data.entries()].filter(([, v]) => typeof v === 'string')
		) as Record<string, string>;

		const errors: Record<string, string> = {};
		if (!/^[a-z][a-z0-9-]{2,39}$/.test(name)) {
			errors.name = 'Use 3–40 lowercase letters, digits and hyphens, starting with a letter.';
		}
		const maxOrderTotal = money(text(data, 'maxOrderTotal'));
		const autoApproveUpTo = money(text(data, 'autoApproveUpTo'));
		const periodSpendCap = money(text(data, 'periodSpendCap'));
		if (!(maxOrderTotal > 0)) errors.maxOrderTotal = 'Enter an order limit above €0.';
		if (!(autoApproveUpTo >= 0))
			errors.autoApproveUpTo = 'Enter €0 or more. €0 sends every order to a person.';
		else if (autoApproveUpTo > maxOrderTotal)
			errors.autoApproveUpTo = 'This can’t be above the order limit.';
		if (!(periodSpendCap >= maxOrderTotal))
			errors.periodSpendCap = 'Make the cap at least the order limit.';

		const reliability = text(data, 'minDeliveryReliability');
		const priceIncrease = text(data, 'maxSubstitutePriceIncreasePct');

		if (Object.keys(errors).length) return fail(400, { errors, values });

		const mandate: Omit<Mandate, 'version'> = {
			maxOrderTotal,
			autoApproveUpTo,
			periodSpendCap,
			spendPeriod: text(data, 'spendPeriod') === 'MONTH' ? 'MONTH' : 'WEEK',
			categorySpendCaps: [],
			allowedCategoryCodes: codes(text(data, 'allowedCategoryCodes')),
			blockedCategoryCodes: [],
			allowedVendors: codes(text(data, 'allowedVendors')),
			blockedVendors: [],
			allowedCountriesOfOrigin: codes(text(data, 'allowedCountriesOfOrigin').toLowerCase()),
			// Checkbox values are "TYPE:ELEMENT", e.g. "FREE_FROM:LACTOSE".
			requiredClaims: data.getAll('requiredClaims').map((c) => {
				const [type, element] = String(c).split(':');
				return { type, element };
			}),
			requiredLabels: [],
			requiredDiets: data.getAll('requiredDiets').map(String),
			excludedAllergens: data.getAll('excludedAllergens').map(String),
			allergenStrictness: (text(data, 'allergenStrictness') || 'contains') as AllergenStrictness,
			substitutionPolicy: (text(data, 'substitutionPolicy') ||
				'IF_REQUIREMENTS_HOLD') as SubstitutionPolicy,
			maxSubstitutePriceIncreasePct: priceIncrease === '' ? null : Number(priceIncrease),
			laterDeliveryNeedsApproval: data.get('laterDeliveryNeedsApproval') === 'on',
			minDeliveryReliability: reliability === '' ? null : Number(reliability) / 100
		};

		const r = await attempt(() =>
			api.agents.create(caller, { name, purpose: text(data, 'purpose'), mandate })
		);
		if (!r.ok) return r.failure;
		redirect(303, `/agents/${r.value.id}?created`);
	}
};
