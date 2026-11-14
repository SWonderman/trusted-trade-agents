<script lang="ts">
	import { resolve } from '$app/paths';
	import type { Mandate, PeriodSpend } from '#lib/api/types.js';
	import { claimText, moneyWhole, percent } from '#lib/format.js';
	import { Progress } from '#lib/components/ui/progress/index.js';

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
		contains: 'Blocks products that contain them',
		may_contain: 'Also blocks “may contain”',
		declared_free: 'Only allows products declared free from them'
	} as const;
	const substitution = {
		NEVER: 'Never substitute',
		IF_REQUIREMENTS_HOLD: 'Allowed when every requirement still holds',
		ALWAYS_NEEDS_APPROVAL: 'Every substitute goes to a person'
	} as const;
	const list = (xs: string[], empty: string) => (xs.length ? xs.join(', ') : empty);
	let period = $derived(m.spendPeriod === 'WEEK' ? 'week' : 'month');
	let used = $derived(Math.min(100, (periodSpend.committed / m.periodSpendCap) * 100));
</script>

{#snippet row(label: string, value: string, hint?: string)}
	<div class="grid gap-1 py-2.5 sm:grid-cols-[11rem_1fr] sm:gap-4">
		<dt class="text-muted-foreground">{label}</dt>
		<dd>
			{value}
			{#if hint}<span class="mt-0.5 block text-xs text-muted-foreground">{hint}</span>{/if}
		</dd>
	</div>
{/snippet}

{#snippet group(title: string, body: import('svelte').Snippet)}
	<section class="rounded-xl border bg-card px-4 py-3">
		<h4 class="text-xs font-medium tracking-wider text-muted-foreground uppercase">{title}</h4>
		<dl class="mt-1 divide-y">{@render body()}</dl>
	</section>
{/snippet}

<div class="space-y-3 text-sm">
	<div class="grid gap-3 sm:grid-cols-3">
		<div class="rounded-xl border bg-card px-4 py-3">
			<p class="text-xs text-muted-foreground">Decides alone up to</p>
			<p class="mt-1 text-xl font-semibold tracking-tight tabular">
				{moneyWhole(m.autoApproveUpTo)}
			</p>
		</div>
		<div class="rounded-xl border bg-card px-4 py-3">
			<p class="text-xs text-muted-foreground">Order limit</p>
			<p class="mt-1 text-xl font-semibold tracking-tight tabular">{moneyWhole(m.maxOrderTotal)}</p>
		</div>
		<div class="rounded-xl border bg-card px-4 py-3">
			<p class="text-xs text-muted-foreground">Spent this {period}</p>
			<p class="mt-1 text-xl font-semibold tracking-tight tabular">
				{moneyWhole(periodSpend.committed)}
				<span class="text-sm font-normal text-muted-foreground"
					>/ {moneyWhole(m.periodSpendCap)}</span
				>
			</p>
			<Progress
				value={used}
				class={['mt-2 h-1.5', used > 85 && '[&>[data-slot=progress-indicator]]:bg-hold']}
				aria-label="Share of the cap used"
			/>
		</div>
	</div>
	<p class="px-1 text-xs text-muted-foreground">
		Above the first figure, orders wait for a person; above the order limit, they’re rejected.
		{moneyWhole(periodSpend.remaining)} left this {period}; splitting orders doesn’t get around the
		cap.
	</p>

	{#snippet assortment()}
		<div class="grid gap-1 py-2.5 sm:grid-cols-[11rem_1fr] sm:gap-4">
			<dt class="text-muted-foreground">Categories</dt>
			<dd>
				{#if m.allowedCategoryCodes.length}
					<span class="mb-1.5 block">Only these {m.allowedCategoryCodes.length}</span>
					<span class="flex flex-wrap gap-1">
						{#each m.allowedCategoryCodes as code (code)}
							<a
								href="{resolve('catalog')}?category={code}"
								class="rounded-md bg-muted px-1.5 py-0.5 code text-xs hover:bg-accent hover:text-accent-foreground"
								>{code}</a
							>
						{/each}
					</span>
				{:else}
					Any category
				{/if}
			</dd>
		</div>
		{#if m.blockedCategoryCodes.length}{@render row(
				'Blocked categories',
				list(m.blockedCategoryCodes, '')
			)}{/if}
		{@render row('Vendors', list(m.allowedVendors, 'Any vendor'))}
		{@render row('Countries of origin', list(m.allowedCountriesOfOrigin, 'Any country'))}
	{/snippet}
	{@render group('Assortment', assortment)}

	{#snippet requirements()}
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
	{/snippet}
	{@render group('Requirements', requirements)}

	{#snippet delivery()}
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
	{/snippet}
	{@render group('Substitutes and delivery', delivery)}
</div>
