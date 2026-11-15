<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import ArrowLeftRightIcon from '@lucide/svelte/icons/arrow-left-right';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
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

	let facts = $derived([
		[
			'Sold per',
			p.salesUnit,
			p.allowedLotSize !== 1 ? `in steps of ${number(p.allowedLotSize)}` : 'whole units'
		],
		[
			'Delivery reliability',
			p.deliveryReliability === null ? 'No history' : percent(p.deliveryReliability),
			p.deliveryReliability === null ? 'not the same as unreliable' : 'delivered as ordered'
		],
		[
			'CO₂ estimate',
			p.carbonFootprint ? `${number(p.carbonFootprint.value)} kg` : '—',
			p.carbonFootprint ? 'per kg, group average' : 'no estimate'
		],
		[
			'Origin',
			p.countryOfOrigin?.toUpperCase() ?? '—',
			p.hasDeposit ? 'returnable packaging' : p.variableUnit ? 'variable weight' : ''
		]
	]);
</script>

<svelte:head><title>{p.name ?? p.code} · Catalog · Saint Elmo</title></svelte:head>

<Dialog.Root
	open
	onOpenChange={(open) => {
		// Back to the same search and filters the product was opened from
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved route, current query
		if (!open) goto(`${resolve('catalog')}${page.url.search}`, { reset: false });
	}}
>
	<Dialog.Content
		class="top-[6dvh] flex max-h-[min(88dvh,52rem)] translate-y-0 flex-col gap-0 overflow-hidden p-0 sm:top-[8dvh] sm:max-w-3xl"
	>
		<!-- Header: what the product is, and what it declares -->
		<header class="border-b px-6 pt-6 pb-5 sm:px-8">
			<p class="flex flex-wrap items-center gap-x-2 gap-y-1 pr-8 text-sm text-muted-foreground">
				<span class="code">{p.code}</span>
				<span>· {p.brand ?? p.vendor}</span>
				<span>· category <span class="code">{p.categoryCode}</span></span>
			</p>
			<Dialog.Title class="mt-2 max-w-[32ch] font-display-tight text-[1.875rem] text-balance">
				{p.name ?? 'Unnamed product'}
			</Dialog.Title>
			<Dialog.Description class="sr-only">
				Product details from the Valio Aimo catalog: claims, allergens, nutrition and packaging.
			</Dialog.Description>
			{#if p.claims.length || p.diets.length || p.labels.length}
				<div class="mt-3 flex flex-wrap gap-1.5">
					{#each p.claims as c (c.type + c.element)}
						<Badge variant="outline" class="font-normal lowercase">
							{c.type.replaceAll('_', ' ')}
							{c.element.replaceAll('_', ' ')}
						</Badge>
					{/each}
					{#each p.diets as d (d)}<Badge variant="secondary" class="font-normal"
							>{d.toLowerCase()}</Badge
						>{/each}
					{#each p.labels as l (l)}<Badge variant="secondary" class="code font-normal">{l}</Badge
						>{/each}
				</div>
			{/if}
		</header>

		<div class="min-h-0 flex-1 space-y-6 overflow-y-auto px-6 py-6 sm:px-8">
			<dl class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
				{#each facts as [label, value, hint] (label)}
					<div>
						<dt class="text-xs text-muted-foreground">{label}</dt>
						<dd class="mt-0.5 text-lg font-semibold tracking-tight tabular">{value}</dd>
						<dd class="text-xs text-muted-foreground">{hint}</dd>
					</div>
				{/each}
			</dl>

			{#if en?.marketingText || en?.keyIngredients}
				<section class="space-y-2 border-t pt-5 text-sm leading-relaxed">
					{#if en.marketingText}<p class="text-pretty">{en.marketingText}</p>{/if}
					{#if en.keyIngredients}
						<p class="text-muted-foreground">
							<span class="font-medium text-foreground">Ingredients:</span>
							{en.keyIngredients}
						</p>
					{/if}
				</section>
			{/if}

			<Tabs.Root value="allergens" class="border-t pt-4">
				<Tabs.List variant="line" class="max-w-full justify-start gap-1 overflow-x-auto sm:gap-4">
					<Tabs.Trigger value="allergens">Allergens</Tabs.Trigger>
					<Tabs.Trigger value="nutrition">Nutrition</Tabs.Trigger>
					<Tabs.Trigger value="packaging">Packaging</Tabs.Trigger>
					<Tabs.Trigger value="substitutes">
						Substitutes <span class="text-muted-foreground tabular"
							>{p.curatedSubstitutes.length}</span
						>
					</Tabs.Trigger>
				</Tabs.List>

				<Tabs.Content value="allergens" class="pt-4">
					{#if p.allergens.length}
						<ul class="divide-y rounded-xl border bg-card">
							{#each p.allergens as a (a.code)}
								{@const c = containment[a.containment]}
								<li class="flex items-center justify-between gap-3 px-4 py-2.5 text-sm">
									<span>{a.name ?? a.code}</span>
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

				<Tabs.Content value="nutrition" class="pt-4">
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

				<Tabs.Content value="packaging" class="pt-4">
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

				<Tabs.Content value="substitutes" class="pt-4">
					{#if p.curatedSubstitutes.length}
						<ul class="divide-y rounded-xl border bg-card">
							{#each p.curatedSubstitutes as sub (sub.code)}
								<li>
									<a
										href="{resolve(`catalog/${sub.code}`)}{page.url.search}"
										data-sveltekit-noscroll
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
							Replacements Valio Aimo itself lists. An agent’s substitute is still judged by its
							mandate.
						</p>
					{:else}
						<p class="text-sm text-muted-foreground">Valio Aimo lists no curated substitutes.</p>
					{/if}
				</Tabs.Content>
			</Tabs.Root>
		</div>

		<footer class="border-t px-6 py-3 text-xs text-muted-foreground sm:px-8">
			{p.provenance.source}, catalog snapshot {p.provenance.catalogSnapshotDate}.
		</footer>
	</Dialog.Content>
</Dialog.Root>
