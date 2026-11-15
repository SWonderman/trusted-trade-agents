<script lang="ts">
	import { resolve } from '$app/paths';
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import ArrowLeftRightIcon from '@lucide/svelte/icons/arrow-left-right';
	import type { OrderLine } from '#lib/api/types.js';
	import { claimText, date, dateTime, money, number, percent, unitName } from '#lib/format.js';
	import { Badge } from '#lib/components/ui/badge/index.js';

	let { line, deliverBy }: { line: OrderLine; deliverBy: string } = $props();

	let o = $derived(line.offer);
	let c = $derived(line.conversion);
	let unit = $derived(line.product.salesUnit);
	let daysLate = $derived(
		Math.round((new Date(o.availableDate).getTime() - new Date(deliverBy).getTime()) / 86_400_000)
	);
	let short = $derived(o.availableAmount !== null && o.availableAmount < line.quantity);
	let closingPassed = $derived(new Date(o.closingTime).getTime() < Date.now());
	let reliability = $derived(line.product.deliveryReliability);
</script>

{#snippet fact(label: string, value: string, hint: string, tone?: 'stop' | 'hold')}
	<div>
		<dt class="text-xs text-muted-foreground">{label}</dt>
		<dd
			class={[
				'mt-0.5 tabular',
				tone === 'stop' && 'font-semibold text-stop',
				tone === 'hold' && 'font-semibold text-hold'
			]}
		>
			{value}
		</dd>
		<dd class="text-xs text-muted-foreground">{hint}</dd>
	</div>
{/snippet}

<article class="rounded-xl border bg-card">
	<header class="flex items-start justify-between gap-x-6 gap-y-2 px-4 pt-4 sm:px-5">
		<div class="min-w-0 flex-1">
			<p class="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
				<span>Line {line.ref.slice(1)}</span>
				<a
					href={resolve(`catalog/${line.product.code}`)}
					class="code underline-offset-2 hover:text-primary hover:underline">{line.product.code}</a
				>
				{#if line.product.vendor}<span>{line.product.vendor}</span>{/if}
			</p>
			<h4 class="mt-1 font-medium text-balance">{line.product.name}</h4>
			{#if line.substitutesFor}
				<p class="mt-1.5 inline-flex items-center gap-1.5 text-sm text-hold">
					<ArrowLeftRightIcon class="size-3.5" aria-hidden="true" />
					Substitute for <span class="code">{line.substitutesFor.code}</span>
					{line.substitutesFor.name}
				</p>
			{/if}
		</div>
		<div class="shrink-0 text-right">
			<p class="text-lg font-semibold tracking-tight tabular">{money(line.lineTotal)}</p>
			<p class="text-xs text-muted-foreground tabular">
				{number(line.quantity)}
				{unit} × {money(o.unitPrice)}
			</p>
		</div>
	</header>

	<!-- The conversion is shown with every quantity it was used for (GLOSSARY: Conversion). -->
	<div class="mx-4 mt-3 rounded-lg bg-muted/70 px-3 py-2.5 text-sm sm:mx-5">
		{#if c}
			<p class="flex flex-wrap items-center gap-x-2 gap-y-1 tabular">
				<span class="font-semibold">{number(c.requested.amount)} {c.requested.unit}</span>
				<ArrowRightIcon class="size-3.5 text-muted-foreground" aria-label="becomes" />
				<span class="font-semibold">{number(c.salesUnits)} {unit}</span>
				<span class="text-muted-foreground">
					1 {unit} ({unitName[unit] ?? unit}) ≈ {number(c.buyerUnitsPerSalesUnit)}
					{c.requested.unit}{#if c.rounded}, rounded up to a multiple of {number(c.lotSize)}{/if}
				</span>
			</p>
			<p class="mt-1 text-xs text-muted-foreground">
				From the {c.method === 'COMPARISON_PRICE'
					? 'price per litre or kilo in the price API'
					: c.method === 'UNIT_CONVERSIONS'
						? 'catalog unit conversions'
						: 'product name'}.
				{c.crossCheck === 'AGREES'
					? 'Cross-checked against the catalog: agrees.'
					: c.crossCheck === 'DISAGREES'
						? 'Cross-check against the catalog disagrees; review the quantity.'
						: 'Not cross-checked.'}
			</p>
		{:else}
			<p>
				<span class="font-semibold tabular">{number(line.quantity)} {unit}</span>
				<span class="text-muted-foreground">ordered directly in sales units, no conversion.</span>
			</p>
		{/if}
	</div>

	<dl class="grid grid-cols-2 gap-x-6 gap-y-4 px-4 py-4 text-sm sm:px-5 lg:grid-cols-3">
		{@render fact(
			'Price',
			`${money(o.comparisonPrice)} per ${o.comparisonUnit === 'L' ? 'litre' : 'kg'}`,
			`valid until ${date(o.priceValidTo)}`
		)}
		{#if o.availableAmount === null}
			{@render fact('Available', 'Unknown', 'shipped by the supplier')}
		{:else}
			{@render fact(
				'Available',
				`${number(o.availableAmount)} ${unit} in Aimo stock`,
				`ordered ${number(line.quantity)}`,
				short ? 'stop' : undefined
			)}
		{/if}
		{@render fact(
			'Delivery',
			date(o.availableDate),
			daysLate > 0
				? `${daysLate} day${daysLate > 1 ? 's' : ''} after ${date(deliverBy)}`
				: `on time for ${date(deliverBy)}`,
			daysLate > 0 ? 'hold' : undefined
		)}
		{@render fact(
			'Order by',
			dateTime(o.closingTime),
			closingPassed ? 'closing time has passed' : 'closing time',
			closingPassed ? 'stop' : undefined
		)}
		{@render fact(
			'Delivery reliability',
			reliability === null ? 'No history' : percent(reliability),
			reliability === null ? 'not the same as unreliable' : 'delivered vs. ordered'
		)}
		{@render fact(
			'CO₂ estimate',
			line.product.carbonFootprint
				? `${number(line.product.carbonFootprint.value)} kg CO₂e/kg`
				: 'No estimate',
			line.product.carbonFootprint ? 'product-group average' : ''
		)}
	</dl>

	<footer
		class="flex flex-wrap items-center gap-1.5 border-t px-4 py-3 text-xs text-muted-foreground sm:px-5"
	>
		{#each line.product.claims as claim (claimText(claim))}
			<Badge variant="outline" class="code font-normal">{claimText(claim)}</Badge>
		{:else}
			<span>No claims declared.</span>
		{/each}
		<span>
			{line.product.claimsSource === 'SYNKKA'
				? 'Declared by the manufacturer (GS1 Synkka).'
				: 'Manufacturer data missing; unknown is not free-from.'}
		</span>
		<span class="ml-auto">Live data fetched {dateTime(o.fetchedAt)}</span>
	</footer>
</article>
