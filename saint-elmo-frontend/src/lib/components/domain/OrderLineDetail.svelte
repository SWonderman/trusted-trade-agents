<script lang="ts">
	import { resolve } from '$app/paths';
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import ArrowLeftRightIcon from '@lucide/svelte/icons/arrow-left-right';
	import type { OrderLine, ProductFacts } from '#lib/api/types.js';
	import type { SubstituteTradeOffs } from '#lib/tradeoffs.js';
	import {
		claimText,
		date,
		dateTime,
		days,
		daysLate,
		lineName,
		lineTotal,
		money,
		number,
		percent,
		unitName
	} from '#lib/format.js';
	import { Badge } from '#lib/components/ui/badge/index.js';

	let {
		line,
		deliverBy,
		product,
		tradeOffs
	}: {
		line: OrderLine;
		deliverBy: string;
		/** The catalog's facts for the product, when the catalog has it. */
		product?: ProductFacts;
		/** Against the product this line substitutes; null when it substitutes nothing. */
		tradeOffs: SubstituteTradeOffs | null;
	} = $props();

	let price = $derived(line.price);
	let availability = $derived(line.availability);
	let quantity = $derived(line.quantity);
	let conversion = $derived(quantity?.conversion ?? null);
	let unit = $derived(line.salesUnit);
	let late = $derived(
		availability?.earliestDate ? daysLate(availability.earliestDate, deliverBy) : 0
	);
	let closingPassed = $derived(
		availability?.closingTime ? new Date(availability.closingTime).getTime() < Date.now() : false
	);
	let reliability = $derived(line.deliveryReliability);
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
				<span>Line {line.position}</span>
				<a
					href={resolve(`catalog/${line.productCode}`)}
					class="code underline-offset-2 hover:text-primary hover:underline">{line.productCode}</a
				>
				{#if product?.vendor}<span>{product.vendor}</span>{/if}
			</p>
			<h4 class="mt-1 font-medium text-balance">
				{lineName(line, product)}
			</h4>
			{#if line.substitutesFor}
				<p class="mt-1.5 inline-flex items-center gap-1.5 text-sm text-hold">
					<ArrowLeftRightIcon class="size-3.5" aria-hidden="true" />
					Substitute for <span class="code">{line.substitutesFor}</span>
					{tradeOffs?.originalName ?? ''}
				</p>
			{/if}
		</div>
		<div class="shrink-0 text-right">
			<p class="text-lg font-semibold tracking-tight tabular">
				{lineTotal(line)}
			</p>
			{#if price}
				<p class="text-xs text-muted-foreground tabular">
					{quantity?.salesUnits != null ? `${number(quantity.salesUnits)} ${unit} × ` : ''}{money(
						price.perSalesUnit.net
					)}
				</p>
			{/if}
		</div>
	</header>

	<!-- The conversion is shown with every quantity it was used for (GLOSSARY: Conversion). -->
	<div class="mx-4 mt-3 rounded-lg bg-muted/70 px-3 py-2.5 text-sm sm:mx-5">
		{#if quantity && conversion && quantity.salesUnits != null}
			<p class="flex flex-wrap items-center gap-x-2 gap-y-1 tabular">
				<span class="font-semibold"
					>{number(quantity.requested.value)} {quantity.requested.unit}</span
				>
				<ArrowRightIcon class="size-3.5 text-muted-foreground" aria-label="becomes" />
				<span class="font-semibold">{number(quantity.salesUnits)} {unit}</span>
				<span class="text-muted-foreground">
					1 {unit} ({unitName[unit] ?? unit}) ≈ {number(conversion.perSalesUnit.value)}
					{conversion.perSalesUnit.unit}{#if quantity.roundedUp}, rounded up to a multiple of {number(
							quantity.lotSize
						)}{/if}{#if quantity.delivered}; delivers {number(quantity.delivered.value)}
						{quantity.delivered.unit}{/if}
				</span>
			</p>
			<p class="mt-1 text-xs text-muted-foreground">
				From the {conversion.basis === 'PRICE_COMPARISON'
					? 'catalog price over the price per litre or kilo'
					: 'product’s packaging units'}.
				{conversion.crossCheck === 'AGREES'
					? 'The product name and packaging agree.'
					: conversion.crossCheck === 'DISAGREES'
						? 'The product name or packaging disagrees; review the quantity.'
						: 'Not cross-checked.'}
			</p>
		{:else if quantity && quantity.salesUnits != null}
			<p>
				<span class="font-semibold tabular">{number(quantity.salesUnits)} {unit}</span>
				<span class="text-muted-foreground">ordered directly in sales units, no conversion.</span>
			</p>
		{:else if quantity}
			<p>
				<span class="font-semibold tabular"
					>{number(quantity.requested.value)} {quantity.requested.unit}</span
				>
				<span class="text-muted-foreground">couldn’t be converted to {unit}.</span>
			</p>
		{:else}
			<p class="text-muted-foreground">No quantity on this line.</p>
		{/if}
	</div>

	<dl class="grid grid-cols-2 gap-x-6 gap-y-4 px-4 py-4 text-sm sm:px-5 lg:grid-cols-3">
		{#if !price}
			{@render fact('Price', 'No price', 'the price API has none for this buyer', 'stop')}
		{:else if price.comparisonPrice}
			{@render fact(
				'Price',
				`${money(price.comparisonPrice.value)} per ${unitName[price.comparisonPrice.unit] ?? price.comparisonPrice.unit}`,
				price.validTo ? `valid until ${date(price.validTo)}` : 'no end date'
			)}
		{:else}
			{@render fact(
				'Price',
				`${money(price.perSalesUnit.net)} per ${unit}`,
				price.validTo ? `valid until ${date(price.validTo)}` : 'no end date'
			)}
		{/if}
		{#if !availability}
			{@render fact('Available', 'Not deliverable', 'left out by the price API', 'stop')}
		{:else if availability.salesBlocked}
			{@render fact('Available', 'Sales blocked', 'Valio Aimo has blocked sales', 'stop')}
		{:else if !availability.availableAmountKnown || availability.availableAmount === null}
			{@render fact('Available', 'Unknown', 'shipped by the supplier')}
		{:else}
			{@render fact(
				'Available',
				`${number(availability.availableAmount)} ${unit} in Aimo stock`,
				quantity?.salesUnits != null ? `ordered ${number(quantity.salesUnits)}` : '',
				quantity?.coveredByAvailability === false ? 'stop' : undefined
			)}
		{/if}
		{#if availability?.earliestDate}
			{@render fact(
				'Delivery',
				date(availability.earliestDate),
				late > 0 ? `${days(late)} after ${date(deliverBy)}` : `on time for ${date(deliverBy)}`,
				late > 0 ? 'hold' : undefined
			)}
		{/if}
		{#if availability?.closingTime}
			{@render fact(
				'Order by',
				dateTime(availability.closingTime),
				closingPassed ? 'closing time has passed' : 'closing time',
				closingPassed ? 'stop' : undefined
			)}
		{/if}
		{@render fact(
			'Delivery reliability',
			reliability === null ? 'No history' : percent(reliability),
			reliability === null ? 'not the same as unreliable' : 'delivered vs. ordered'
		)}
		{@render fact(
			'CO₂ estimate',
			line.carbonFootprint ? `${number(line.carbonFootprint.value)} kg CO₂e/kg` : 'No estimate',
			line.carbonFootprint ? 'product-group average' : ''
		)}
	</dl>

	{#if tradeOffs}
		{@const declared = tradeOffs.declared}
		<section class="mx-4 mb-4 rounded-lg border border-hold/25 px-3 py-2.5 text-sm sm:mx-5">
			<h5 class="text-xs font-medium text-hold">Against the product it replaces</h5>
			<ul class="mt-1 space-y-0.5">
				{#if tradeOffs.pricePerUnitDeltaPct !== null}
					<li class="tabular">
						{tradeOffs.pricePerUnitDeltaPct > 0
							? `${number(tradeOffs.pricePerUnitDeltaPct)}% dearer`
							: tradeOffs.pricePerUnitDeltaPct < 0
								? `${number(-tradeOffs.pricePerUnitDeltaPct)}% cheaper`
								: 'Same price'} per {unitName[price?.comparisonPrice?.unit ?? ''] ?? 'unit'}
					</li>
				{/if}
				{#if tradeOffs.daysLater}
					<li class="tabular">
						{tradeOffs.daysLater > 0
							? `Arrives ${days(tradeOffs.daysLater)} later`
							: `Arrives ${days(-tradeOffs.daysLater)} sooner`}
					</li>
				{/if}
				{#each tradeOffs.reasons as reason (reason.code)}
					<li><span class="code text-xs">{reason.code}</span> {reason.message}</li>
				{/each}
				{#if declared?.lost.length}
					<li>
						Loses
						{#each declared.lost as k (k)}<Badge variant="outline" class="ml-1 code font-normal"
								>{k}</Badge
							>{/each}
					</li>
				{/if}
				{#if declared?.gained.length}
					<li>
						Adds
						{#each declared.gained as k (k)}<Badge variant="outline" class="ml-1 code font-normal"
								>{k}</Badge
							>{/each}
					</li>
				{/if}
				{#if declared && !declared.lost.length && !declared.gained.length}
					<li class="text-muted-foreground">Same declared claims, diets and labels.</li>
				{/if}
				{#if declared?.vendors}
					<li class="text-muted-foreground">
						From {declared.vendors.substitute}, not {declared.vendors.original}.
					</li>
				{/if}
			</ul>
			{#if !declared}
				<p class="mt-1 text-xs text-muted-foreground">
					The catalog has no declared claims for both products to compare.
				</p>
			{/if}
		</section>
	{/if}

	<footer
		class="flex flex-wrap items-center gap-1.5 border-t px-4 py-3 text-xs text-muted-foreground sm:px-5"
	>
		{#each line.reasonCodes as code (code)}
			<Badge variant="outline" class="border-hold/40 code font-normal text-hold">{code}</Badge>
		{/each}
		{#if product}
			{#each product.claims as claim (claimText(claim))}
				<Badge variant="outline" class="code font-normal">{claimText(claim)}</Badge>
			{:else}
				<span>No claims declared; unknown is not free-from.</span>
			{/each}
		{:else}
			<span>Not in the catalog Saint Elmo reads, so no declared claims to show.</span>
		{/if}
		<span class="ml-auto">
			Live data fetched {dateTime(line.provenance.fetchedAt)}{line.provenance.cached
				? ' (cached)'
				: ''}
		</span>
	</footer>
</article>
