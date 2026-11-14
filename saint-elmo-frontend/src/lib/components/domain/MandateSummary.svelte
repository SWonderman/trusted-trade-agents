<script lang="ts">
	import type { Mandate, PeriodSpend } from '#lib/api/types.js';
	import { claimText, moneyWhole, percent } from '#lib/format.js';

	let { mandate: m, periodSpend }: { mandate: Mandate; periodSpend: PeriodSpend } = $props();

	const allergenNames: Record<string, string> = {
		AM: 'milk',
		AW: 'gluten cereals',
		UW: 'wheat',
		AE: 'egg',
		AN: 'tree nuts',
		AY: 'soy',
		AP: 'peanuts',
		AF: 'fish'
	};
	const strictness = {
		contains: 'Block products that contain them',
		may_contain: 'Also block “may contain”',
		declared_free: 'Only allow products declared free from them'
	} as const;
	const substitution = {
		NEVER: 'Never substitute',
		IF_REQUIREMENTS_HOLD: 'Allowed when every requirement still holds',
		ALWAYS_NEEDS_APPROVAL: 'Every substitute goes to a person'
	} as const;
	const list = (xs: string[], empty: string) => (xs.length ? xs.join(', ') : empty);
	let period = $derived(m.spendPeriod === 'WEEK' ? 'week' : 'month');
</script>

{#snippet row(label: string, value: string, hint?: string)}
	<div class="grid grid-cols-[11rem_1fr] gap-3 py-2">
		<dt class="text-muted">{label}</dt>
		<dd class="text-ink">
			{value}
			{#if hint}<span class="block text-xs text-muted">{hint}</span>{/if}
		</dd>
	</div>
{/snippet}

<div class="space-y-6 text-sm">
	<section aria-labelledby="m-spend">
		<h4 id="m-spend" class="font-semibold text-ink">Spend</h4>
		<dl class="mt-1 divide-y divide-line">
			{@render row(
				'Decides alone up to',
				moneyWhole(m.autoApproveUpTo),
				'Above this, orders wait for a person.'
			)}
			{@render row(
				'Order limit',
				moneyWhole(m.maxOrderTotal),
				'Orders above this are rejected outright.'
			)}
			{@render row(
				`Cap per ${period}`,
				moneyWhole(m.periodSpendCap),
				`${moneyWhole(periodSpend.committed)} committed, ${moneyWhole(periodSpend.remaining)} left. Splitting orders doesn’t get around it.`
			)}
		</dl>
	</section>

	<section aria-labelledby="m-assort">
		<h4 id="m-assort" class="font-semibold text-ink">Assortment</h4>
		<dl class="mt-1 divide-y divide-line">
			{@render row('Categories', list(m.allowedCategoryCodes, 'Any category'))}
			{#if m.blockedCategoryCodes.length}{@render row(
					'Blocked categories',
					list(m.blockedCategoryCodes, '')
				)}{/if}
			{@render row('Vendors', list(m.allowedVendors, 'Any vendor'))}
			{@render row('Countries of origin', list(m.allowedCountriesOfOrigin, 'Any country'))}
		</dl>
	</section>

	<section aria-labelledby="m-req">
		<h4 id="m-req" class="font-semibold text-ink">Requirements</h4>
		<dl class="mt-1 divide-y divide-line">
			{@render row(
				'Required claims',
				list(m.requiredClaims.map(claimText), 'None'),
				m.requiredClaims.length ? 'Unknown counts as missing.' : undefined
			)}
			{@render row(
				'Excluded allergens',
				list(
					m.excludedAllergens.map((a) => `${a} (${allergenNames[a] ?? a})`),
					'None'
				),
				m.excludedAllergens.length ? strictness[m.allergenStrictness] : undefined
			)}
			{#if m.requiredLabels.length}{@render row('Required labels', list(m.requiredLabels, ''))}{/if}
		</dl>
	</section>

	<section aria-labelledby="m-sub">
		<h4 id="m-sub" class="font-semibold text-ink">Substitutes and delivery</h4>
		<dl class="mt-1 divide-y divide-line">
			{@render row(
				'Substitutes',
				substitution[m.substitutionPolicy],
				m.maxSubstitutePriceIncreasePct !== null
					? `Price per litre or kg may rise at most ${m.maxSubstitutePriceIncreasePct}%.`
					: undefined
			)}
			{@render row(
				'Later delivery',
				m.laterDeliveryNeedsApproval ? 'Needs a person' : 'Accepted without asking'
			)}
			{@render row(
				'Minimum reliability',
				m.minDeliveryReliability === null ? 'No minimum' : percent(m.minDeliveryReliability),
				'Products with no delivery history aren’t held back.'
			)}
		</dl>
	</section>
</div>
