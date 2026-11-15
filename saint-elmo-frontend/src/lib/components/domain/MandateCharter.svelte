<script lang="ts">
	import { resolve } from '$app/paths';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import type { Mandate, PeriodSpend } from '#lib/api/types.js';
	import { moneyWhole, percent } from '#lib/format.js';
	import * as Collapsible from '#lib/components/ui/collapsible/index.js';
	import { Progress } from '#lib/components/ui/progress/index.js';

	/**
	 * A mandate written out as the buyer admin would say it, with every limit in view.
	 * The full list of rules is one click away for the details.
	 */
	let {
		mandate: m,
		periodSpend,
		rulesOpen = false
	}: {
		mandate: Mandate;
		periodSpend: PeriodSpend;
		/** Show every rule directly instead of behind a toggle. */
		rulesOpen?: boolean;
	} = $props();

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
	const human = (s: string) => s.replaceAll('_', ' ').toLowerCase();
	const list = (xs: string[]) =>
		xs.length <= 1 ? (xs[0] ?? '') : `${xs.slice(0, -1).join(', ')} and ${xs.at(-1)}`;

	let period = $derived(m.spendPeriod === 'WEEK' ? 'week' : 'month');
	let claims = $derived(list(m.requiredClaims.map((c) => `${human(c.type)} ${human(c.element)}`)));
	let diets = $derived(list(m.requiredDiets.map(human)));
	let allergens = $derived(list(m.excludedAllergens.map((a) => allergenNames[a] ?? a)));
	let used = $derived(Math.min(100, (periodSpend.committed / m.periodSpendCap) * 100));
</script>

{#snippet rules()}
	<dl class="divide-y rounded-xl border bg-card text-sm">
		<div class="grid gap-2 px-4 py-3 sm:grid-cols-[10rem_1fr]">
			<dt class="text-muted-foreground">Categories</dt>
			<dd>
				{#if m.allowedCategoryCodes.length}
					<span class="flex flex-wrap gap-1">
						{#each m.allowedCategoryCodes as code (code)}
							<a
								href="{resolve('catalog')}?category={code}"
								class="rounded-md bg-muted px-1.5 py-0.5 code text-xs hover:bg-accent">{code}</a
							>
						{/each}
					</span>
				{:else}
					Any category
				{/if}
			</dd>
		</div>
		{#each [['Vendors', m.allowedVendors.length ? m.allowedVendors.join(', ') : 'Any vendor'], ['Countries of origin', m.allowedCountriesOfOrigin.length ? m.allowedCountriesOfOrigin
							.join(', ')
							.toUpperCase() : 'Any country'], ['Required labels', m.requiredLabels.length ? m.requiredLabels.join(', ') : 'None'], ['Delivery reliability', m.minDeliveryReliability === null ? 'No minimum' : `At least ${percent(m.minDeliveryReliability)}`]] as [label, value] (label)}
			<div class="grid gap-2 px-4 py-3 sm:grid-cols-[10rem_1fr]">
				<dt class="text-muted-foreground">{label}</dt>
				<dd>{value}</dd>
			</div>
		{/each}
	</dl>
{/snippet}

{#snippet v(text: string)}<mark class="val">{text}</mark>{/snippet}

<div class="space-y-6">
	<div class="writ space-y-3">
		<p>
			It may order up to {@render v(moneyWhole(m.autoApproveUpTo))} on its own, and never more than
			{@render v(moneyWhole(m.maxOrderTotal))} at once, within {@render v(
				moneyWhole(m.periodSpendCap)
			)}
			a {period}.
		</p>
		<p>
			{#if m.allowedCategoryCodes.length}
				It buys only from {@render v(
					`${m.allowedCategoryCodes.length} categories`
				)}{#if claims || diets}, and everything must be {@render v(
						[claims, diets].filter(Boolean).join(' and ')
					)}{/if}.
			{:else if claims || diets}
				Everything it buys must be {@render v([claims, diets].filter(Boolean).join(' and '))}.
			{:else}
				It may buy any product.
			{/if}
			{#if allergens}
				{#if m.allergenStrictness === 'declared_free'}
					Every product must be declared free from {@render v(allergens)}.
				{:else}
					Nothing may contain {@render v(allergens)}{#if m.allergenStrictness === 'may_contain'},
						not even possibly{/if}.
				{/if}
			{/if}
		</p>
		<p>
			{#if m.substitutionPolicy === 'NEVER'}
				It may {@render v('never substitute')}.
			{:else if m.substitutionPolicy === 'ALWAYS_NEEDS_APPROVAL'}
				Every substitute {@render v('goes to a person')}.
			{:else}
				Substitutes are {@render v(
					'allowed when every requirement still holds'
				)}{#if m.maxSubstitutePriceIncreasePct !== null}, at most {@render v(
						`${m.maxSubstitutePriceIncreasePct}%`
					)} dearer per litre{/if}.
			{/if}
			A later delivery {@render v(
				m.laterDeliveryNeedsApproval ? 'waits for a person' : 'is accepted'
			)}.
		</p>
	</div>

	<div>
		<div class="flex items-baseline justify-between gap-3 text-sm">
			<span class="text-muted-foreground">Spent this {period}</span>
			<span class="font-medium tabular">
				{moneyWhole(periodSpend.committed)}
				<span class="font-normal text-muted-foreground">of {moneyWhole(m.periodSpendCap)}</span>
			</span>
		</div>
		<Progress
			value={used}
			class={['mt-2 h-1.5', used > 85 && '[&>[data-slot=progress-indicator]]:bg-hold']}
			aria-label="Share of the spend cap used"
		/>
	</div>

	{#if rulesOpen}
		<section aria-labelledby="rules-heading">
			<h4 id="rules-heading" class="mb-3 text-sm font-semibold">Every rule</h4>
			{@render rules()}
		</section>
	{:else}
		<Collapsible.Root>
			<Collapsible.Trigger
				class="group/rules inline-flex items-center gap-1 text-sm font-medium hover:underline"
			>
				Every rule
				<ChevronDownIcon
					class="size-4 transition-transform group-data-[state=open]/rules:rotate-180"
					aria-hidden="true"
				/>
			</Collapsible.Trigger>
			<Collapsible.Content class="mt-3">
				{@render rules()}
			</Collapsible.Content>
		</Collapsible.Root>
	{/if}
</div>

<style>
	.writ {
		font-family: var(--font-display);
		font-size: 1.25rem;
		line-height: 1.55;
		text-wrap: pretty;
	}
	.val {
		background: none;
		color: inherit;
		font-weight: 600;
		box-shadow: inset 0 -0.35em 0 oklch(0.84 0.085 86 / 0.5);
		border-radius: 2px;
		padding-inline: 0.08em;
	}
</style>
