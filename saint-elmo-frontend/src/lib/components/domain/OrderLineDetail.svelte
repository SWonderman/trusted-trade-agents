<script lang="ts">
	import type { OrderLine } from '#lib/api/types.js';
	import { claimText, date, dateTime, money, number, percent, unitName } from '#lib/format.js';
	import Icon from '../ui/Icon.svelte';

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

<article class="py-5 first:pt-0 last:pb-0">
	<header class="grid grid-cols-[1fr_auto] items-start gap-x-6 gap-y-2">
		<div class="min-w-0">
			<p class="flex flex-wrap gap-x-3 text-xs text-muted">
				<span>Line {line.ref.slice(1)}</span>
				<span class="code">{line.product.code}</span>
				{#if line.product.vendor}<span>{line.product.vendor}</span>{/if}
			</p>
			<h3 class="mt-0.5 font-semibold text-ink">{line.product.name}</h3>
			{#if line.substitutesFor}
				<p class="mt-1 text-sm text-hold">
					<span class="mr-1 inline-block translate-y-0.5"><Icon name="swap" size={14} /></span
					>Substitute for <span class="code">{line.substitutesFor.code}</span>
					{line.substitutesFor.name}
				</p>
			{/if}
		</div>
		<div class="text-right">
			<p class="tabular text-lg font-semibold text-ink">{money(line.lineTotal)}</p>
			<p class="tabular text-xs text-muted">
				{number(line.quantity)}
				{unit} × {money(o.unitPrice)}
			</p>
		</div>
	</header>

	<!-- The conversion is shown with every quantity it was used for (GLOSSARY: Conversion). -->
	<div class="mt-3 rounded-sm border border-line bg-surface px-3 py-2.5 text-sm">
		{#if c}
			<p class="tabular flex flex-wrap items-center gap-x-2 gap-y-1 text-ink">
				<span class="font-semibold">{number(c.requested.amount)} {c.requested.unit}</span>
				<Icon name="arrowRight" size={14} />
				<span class="font-semibold">{number(c.salesUnits)} {unit}</span>
				<span class="text-muted">
					1 {unit} ({unitName[unit] ?? unit}) ≈ {number(c.buyerUnitsPerSalesUnit)}
					{c.requested.unit}{#if c.rounded}, rounded up to a multiple of {number(c.lotSize)}{/if}
				</span>
			</p>
			<p class="mt-1 text-xs text-muted">
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
			<p class="text-ink">
				<span class="tabular font-semibold">{number(line.quantity)} {unit}</span>
				<span class="text-muted">ordered directly in sales units, no conversion used.</span>
			</p>
		{/if}
	</div>

	<dl class="mt-3 grid grid-cols-2 gap-x-6 gap-y-3 text-sm lg:grid-cols-3">
		<div>
			<dt class="text-xs text-muted">Price</dt>
			<dd class="tabular text-ink">
				{money(o.comparisonPrice)} per {o.comparisonUnit === 'L' ? 'litre' : 'kg'}
			</dd>
			<dd class="text-xs text-muted">valid until {date(o.priceValidTo)}</dd>
		</div>
		<div>
			<dt class="text-xs text-muted">Available</dt>
			{#if o.availableAmount === null}
				<dd class="text-ink">Unknown</dd>
				<dd class="text-xs text-muted">shipped by the supplier</dd>
			{:else}
				<dd class={['tabular', short ? 'font-semibold text-stop' : 'text-ink']}>
					{number(o.availableAmount)}
					{unit} in Aimo stock
				</dd>
				<dd class="text-xs text-muted">ordered {number(line.quantity)}</dd>
			{/if}
		</div>
		<div>
			<dt class="text-xs text-muted">Delivery</dt>
			<dd class={daysLate > 0 ? 'font-semibold text-hold' : 'text-ink'}>{date(o.availableDate)}</dd>
			<dd class="text-xs text-muted">
				{daysLate > 0
					? `${daysLate} day${daysLate > 1 ? 's' : ''} after ${date(deliverBy)}`
					: `on time for ${date(deliverBy)}`}
			</dd>
		</div>
		<div>
			<dt class="text-xs text-muted">Order by</dt>
			<dd class={closingPassed ? 'font-semibold text-stop' : 'text-ink'}>
				{dateTime(o.closingTime)}
			</dd>
			<dd class="text-xs text-muted">
				{closingPassed ? 'closing time has passed' : 'closing time'}
			</dd>
		</div>
		<div>
			<dt class="text-xs text-muted">Delivery reliability</dt>
			<dd class="tabular text-ink">{reliability === null ? 'No history' : percent(reliability)}</dd>
			<dd class="text-xs text-muted">
				{reliability === null ? 'not the same as unreliable' : 'delivered vs. ordered'}
			</dd>
		</div>
		<div>
			<dt class="text-xs text-muted">CO₂ estimate</dt>
			{#if line.product.carbonFootprint}
				<dd class="tabular text-ink">{number(line.product.carbonFootprint.value)} kg CO₂e/kg</dd>
				<dd class="text-xs text-muted">product-group average</dd>
			{:else}
				<dd class="text-ink">No estimate</dd>
			{/if}
		</div>
	</dl>

	<p class="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-muted">
		{#each line.product.claims as claim (claimText(claim))}
			<span class="code rounded-sm border border-line px-1.5 py-0.5 text-ink"
				>{claimText(claim)}</span
			>
		{:else}
			<span>No claims declared.</span>
		{/each}
		<span>
			{line.product.claimsSource === 'SYNKKA'
				? 'Declared by the manufacturer (GS1 Synkka).'
				: 'Manufacturer data missing; unknown is not free-from.'}
		</span>
		<span>Live data fetched {dateTime(o.fetchedAt)}.</span>
	</p>
</article>
