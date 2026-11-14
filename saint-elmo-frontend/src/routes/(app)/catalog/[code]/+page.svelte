<script lang="ts">
	import { resolve } from '$app/paths';
	import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';
	import ArrowLeftRightIcon from '@lucide/svelte/icons/arrow-left-right';
	import DataSource from '#lib/components/app/DataSource.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Table from '#lib/components/ui/table/index.js';
	import * as Tabs from '#lib/components/ui/tabs/index.js';
	import { number, percent } from '#lib/format.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let p = $derived(data.product);
	let en = $derived(p.translations.find((t) => t.language === 'en') ?? p.translations[0]);
	const containment: Record<string, { label: string; cls: string }> = {
		CONTAINS: { label: 'Contains', cls: 'bg-stop/10 text-stop ring-stop/20' },
		MAY_CONTAIN: { label: 'May contain', cls: 'bg-hold/12 text-hold ring-hold/25' },
		UNDECLARED: { label: 'Undeclared', cls: 'bg-muted text-muted-foreground ring-border' },
		FREE_FROM: { label: 'Free from', cls: 'bg-ok/10 text-ok ring-ok/20' }
	};
	const per100 = (n: (typeof p.nutrients)[number]) =>
		n.basisQuantity ? `per ${number(n.basisQuantity)} ${n.basisUnit ?? ''}` : '';
</script>

<svelte:head><title>{p.name ?? p.code} · Catalog · Saint Elmo</title></svelte:head>

<Button href={resolve('catalog')} variant="ghost" size="sm" class="mb-4 -ml-2">
	<ArrowLeftIcon /> Catalog
</Button>

<header class="mb-8">
	<p class="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
		<span class="code">{p.code}</span>
		<span>{p.vendor}</span>
		{#if p.brand}<span>· {p.brand}</span>{/if}
		<span>· category <span class="code">{p.categoryCode}</span></span>
		<DataSource mode={data.source} />
	</p>
	<h1 class="mt-2 max-w-[28ch] font-display-tight text-[2.375rem] text-balance">
		{p.name ?? 'Unnamed product'}
	</h1>
	<div class="mt-4 flex flex-wrap gap-1.5">
		{#each p.claims as c (c.type + c.element)}
			<Badge variant="outline" class="font-normal lowercase">
				{c.type.replaceAll('_', ' ')}
				{c.element.replaceAll('_', ' ')}
			</Badge>
		{/each}
		{#each p.diets as d (d)}<Badge variant="secondary" class="font-normal">{d.toLowerCase()}</Badge
			>{/each}
		{#each p.labels as l (l)}<Badge variant="secondary" class="code font-normal">{l}</Badge>{/each}
	</div>
</header>

<div class="max-w-5xl">
	<div class="min-w-0 space-y-6">
		<dl class="grid grid-cols-2 gap-3 md:grid-cols-4">
			{#each [['Sold per', `${p.salesUnit}`, p.allowedLotSize !== 1 ? `in steps of ${number(p.allowedLotSize)}` : 'whole units'], ['Delivery reliability', p.deliveryReliability === null ? 'No history' : percent(p.deliveryReliability), p.deliveryReliability === null ? 'not the same as unreliable' : 'delivered as ordered'], ['CO₂ estimate', p.carbonFootprint ? `${number(p.carbonFootprint.value)} kg` : '—', p.carbonFootprint ? 'CO₂e per kg, group average' : 'no estimate'], ['Origin', p.countryOfOrigin?.toUpperCase() ?? '—', p.hasDeposit ? 'returnable packaging' : p.variableUnit ? 'variable weight' : '']] as [label, value, hint] (label)}
				<div class="rounded-xl border bg-card px-4 py-3">
					<dt class="text-xs text-muted-foreground">{label}</dt>
					<dd class="mt-1 text-lg font-semibold tracking-tight tabular">{value}</dd>
					<dd class="text-xs text-muted-foreground">{hint}</dd>
				</div>
			{/each}
		</dl>

		{#if en?.marketingText || en?.keyIngredients}
			<section class="rounded-xl border bg-card px-5 py-4 text-sm leading-relaxed">
				{#if en.marketingText}<p class="text-pretty">{en.marketingText}</p>{/if}
				{#if en.keyIngredients}
					<p class={['text-muted-foreground', en.marketingText && 'mt-3']}>
						<span class="font-medium text-foreground">Ingredients:</span>
						{en.keyIngredients}
					</p>
				{/if}
			</section>
		{/if}

		<Tabs.Root value="allergens">
			<Tabs.List>
				<Tabs.Trigger value="allergens">Allergens</Tabs.Trigger>
				<Tabs.Trigger value="nutrition">Nutrition</Tabs.Trigger>
				<Tabs.Trigger value="packaging">Packaging</Tabs.Trigger>
				<Tabs.Trigger value="substitutes">
					Substitutes <span class="text-muted-foreground tabular"
						>{p.curatedSubstitutes.length}</span
					>
				</Tabs.Trigger>
			</Tabs.List>

			<Tabs.Content value="allergens" class="pt-3">
				{#if p.allergens.length}
					<ul class="grid gap-2 sm:grid-cols-2">
						{#each p.allergens as a (a.code)}
							{@const c = containment[a.containment]}
							<li
								class="flex items-center justify-between gap-3 rounded-lg border bg-card px-3 py-2 text-sm"
							>
								<span>
									{a.name ?? a.code}
									<span class="code text-muted-foreground">{a.code}</span>
								</span>
								<span class={['rounded-full px-2 py-0.5 text-xs ring-1 ring-inset', c.cls]}
									>{c.label}</span
								>
							</li>
						{/each}
					</ul>
				{/if}
				<p class="mt-3 text-xs text-muted-foreground">
					{p.allergens.length
						? 'An allergen missing from this list has unknown status, never free-from.'
						: 'The manufacturer declared no allergen data. Unknown is not free-from.'}
				</p>
			</Tabs.Content>

			<Tabs.Content value="nutrition" class="pt-3">
				{#if p.nutrients.length}
					<div class="overflow-hidden rounded-xl border bg-card">
						<Table.Root>
							<Table.Body>
								{#each p.nutrients as n (n.code)}
									<Table.Row>
										<Table.Cell class="pl-4 code">{n.code}</Table.Cell>
										<Table.Cell class="text-right tabular">
											{n.precision === 'LESS_THAN' ? '< ' : ''}{number(n.value)}
											{n.unit}
										</Table.Cell>
										<Table.Cell class="pr-4 text-right text-xs text-muted-foreground"
											>{per100(n)}</Table.Cell
										>
									</Table.Row>
								{/each}
							</Table.Body>
						</Table.Root>
					</div>
				{:else}
					<p class="text-sm text-muted-foreground">No nutrition data declared.</p>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="packaging" class="pt-3">
				<div class="overflow-hidden rounded-xl border bg-card">
					<Table.Root>
						<Table.Header>
							<Table.Row class="bg-muted/50 hover:bg-muted/50">
								<Table.Head class="pl-4">Unit</Table.Head>
								<Table.Head class="text-right">Base units ({p.baseUnit})</Table.Head>
								<Table.Head class="pr-4">GTIN</Table.Head>
							</Table.Row>
						</Table.Header>
						<Table.Body>
							{#each p.units as u (u.code)}
								<Table.Row>
									<Table.Cell class="pl-4 code">
										{u.code}
										{#if u.code === p.salesUnit}<Badge variant="secondary" class="ml-1 font-sans"
												>sales unit</Badge
											>{/if}
									</Table.Cell>
									<Table.Cell class="text-right tabular">{number(u.sizeInBaseUnits)}</Table.Cell>
									<Table.Cell class="pr-4 code text-muted-foreground">{u.gtin ?? '—'}</Table.Cell>
								</Table.Row>
							{/each}
						</Table.Body>
					</Table.Root>
				</div>
			</Tabs.Content>

			<Tabs.Content value="substitutes" class="pt-3">
				{#if p.curatedSubstitutes.length}
					<ul class="divide-y rounded-xl border bg-card">
						{#each p.curatedSubstitutes as sub (sub.code)}
							<li>
								<a
									href={resolve(`catalog/${sub.code}`)}
									class="flex items-center gap-3 px-4 py-3 text-sm hover:bg-muted/50"
								>
									<ArrowLeftRightIcon class="size-4 text-muted-foreground" aria-hidden="true" />
									<span class="flex-1">{sub.name ?? 'Unnamed product'}</span>
									<span class="code text-muted-foreground">{sub.code}</span>
								</a>
							</li>
						{/each}
					</ul>
					<p class="mt-3 text-xs text-muted-foreground">
						Curated substitutes: replacements Valio Aimo itself lists. An agent’s substitute is
						still judged by its mandate.
					</p>
				{:else}
					<p class="text-sm text-muted-foreground">Valio Aimo lists no curated substitutes.</p>
				{/if}
			</Tabs.Content>
		</Tabs.Root>

		<p class="text-xs text-muted-foreground">
			{p.provenance.source}, catalog snapshot {p.provenance.catalogSnapshotDate}.
		</p>
	</div>
</div>
