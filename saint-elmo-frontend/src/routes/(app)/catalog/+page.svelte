<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { navigating, page } from '$app/state';
	import ChevronLeftIcon from '@lucide/svelte/icons/chevron-left';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import PackageSearchIcon from '@lucide/svelte/icons/package-search';
	import SearchIcon from '@lucide/svelte/icons/search';
	import SlidersHorizontalIcon from '@lucide/svelte/icons/sliders-horizontal';
	import XIcon from '@lucide/svelte/icons/x';
	import PageHeader from '#lib/components/app/PageHeader.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Checkbox } from '#lib/components/ui/checkbox/index.js';
	import * as Empty from '#lib/components/ui/empty/index.js';
	import * as InputGroup from '#lib/components/ui/input-group/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import * as Table from '#lib/components/ui/table/index.js';
	import { number, percent } from '#lib/format.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let s = $derived(data.search);
	let q = $derived(s.q);
	let loading = $derived(navigating.to?.url.pathname === '/catalog');
	// On small screens the filters fold away, so results come first.
	let showFilters = $state(false);

	const ALL = '__all';
	const count = new Intl.NumberFormat('en-GB');
	const strictnessLabel = {
		contains: 'Drop products that contain them',
		may_contain: 'Also drop “may contain”',
		declared_free: 'Keep only declared free'
	} as const;
	const statusTone: Record<string, string> = {
		CONTAINS: 'bg-stop/10 text-stop ring-stop/20',
		MAY_CONTAIN: 'bg-hold/12 text-hold ring-hold/25',
		FREE_FROM: 'bg-ok/10 text-ok ring-ok/20'
	};

	// The most used free-from claims and allergens make useful one-click filters.
	let claimOptions = $derived(
		(data.vocabulary?.claims ?? [])
			.filter((c) => c.type.code === 'FREE_FROM')
			.toSorted((a, b) => b.productCount - a.productCount)
			.slice(0, 8)
	);
	let allergenOptions = $derived(
		(data.vocabulary?.allergens ?? [])
			.toSorted((a, b) => b.productCount - a.productCount)
			.slice(0, 10)
	);
	let allergenName = $derived(
		new Map((data.vocabulary?.allergens ?? []).map((a) => [a.code, a.name ?? a.code]))
	);
	let categories = $derived(
		(data.vocabulary?.categories ?? []).toSorted((a, b) => a.code.localeCompare(b.code))
	);
	let filtered = $derived(Boolean(s.q || s.category || s.claims.length || s.allergens.length));
	let pages = $derived(data.results ? Math.ceil(data.results.total / data.pageSize) : 0);

	function update(mutate: (p: URLSearchParams) => void) {
		const url = new URL(page.url.href);
		mutate(url.searchParams);
		url.searchParams.delete('page');
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- same resolved route, new query only
		goto(`${resolve('catalog')}${url.search}`, { reset: false });
	}
	function toggle(key: string, value: string, on: boolean) {
		update((p) => {
			const rest = p.getAll(key).filter((v) => v !== value);
			p.delete(key);
			for (const v of on ? [...rest, value] : rest) p.append(key, v);
		});
	}
	function pageHref(n: number) {
		const url = new URL(page.url.href);
		url.searchParams.set('page', String(n));
		return url.pathname + url.search;
	}
</script>

<svelte:head><title>Catalog · Saint Elmo</title></svelte:head>

<PageHeader
	title="Catalog"
	source={data.source}
	description="The Valio Aimo products your agents search, with the claims, allergens and categories a mandate can require or rule out. Missing manufacturer data is shown as unknown, never as free-from."
/>

<div class="grid items-start gap-6 lg:grid-cols-[17rem_1fr]">
	<aside class="space-y-5 rounded-xl border bg-card p-4 lg:sticky lg:top-20" aria-label="Filters">
		<form
			role="search"
			onsubmit={(e) => {
				e.preventDefault();
				update((p) => (q.trim() ? p.set('q', q.trim()) : p.delete('q')));
			}}
		>
			<Label for="q" class="sr-only">Search products</Label>
			<InputGroup.Root>
				<InputGroup.Addon><SearchIcon /></InputGroup.Addon>
				<InputGroup.Input id="q" placeholder="Name, brand or code" bind:value={q} />
				{#if loading}<InputGroup.Addon align="inline-end"><Spinner /></InputGroup.Addon>{/if}
			</InputGroup.Root>
			<p class="mt-1.5 text-xs text-muted-foreground">Finnish, Swedish and English names.</p>
		</form>

		{#if data.vocabulary}
			<Button
				variant="outline"
				size="sm"
				class="w-full lg:hidden"
				aria-expanded={showFilters}
				aria-controls="catalog-filters"
				onclick={() => (showFilters = !showFilters)}
			>
				<SlidersHorizontalIcon />
				{showFilters ? 'Hide filters' : 'Filters'}
				{#if s.claims.length + s.allergens.length + (s.category ? 1 : 0)}
					<span class="rounded-full bg-primary px-1.5 text-xs text-primary-foreground tabular">
						{s.claims.length + s.allergens.length + (s.category ? 1 : 0)}
					</span>
				{/if}
			</Button>
			<div id="catalog-filters" class={['space-y-5', !showFilters && 'max-lg:hidden']}>
				<fieldset class="space-y-2.5">
					<legend class="mb-2 text-sm font-medium">Must be free from</legend>
					{#each claimOptions as c (c.element.code)}
						{@const value = `FREE_FROM:${c.element.code}`}
						<div class="flex items-center gap-2">
							<Checkbox
								id="claim-{c.element.code}"
								checked={s.claims.includes(value)}
								onCheckedChange={(on) => toggle('claim', value, on)}
							/>
							<Label for="claim-{c.element.code}" class="flex-1 font-normal capitalize">
								{(c.element.name ?? c.element.code).toLowerCase()}
							</Label>
							<span class="text-xs text-muted-foreground tabular"
								>{count.format(c.productCount)}</span
							>
						</div>
					{/each}
				</fieldset>

				<div class="border-t"></div>
				<fieldset class="space-y-2.5">
					<legend class="mb-2 text-sm font-medium">Exclude allergens</legend>
					{#each allergenOptions as a (a.code)}
						<div class="flex items-center gap-2">
							<Checkbox
								id="allergen-{a.code}"
								checked={s.allergens.includes(a.code)}
								onCheckedChange={(on) => toggle('allergen', a.code, on)}
							/>
							<Label for="allergen-{a.code}" class="min-w-0 flex-1 justify-between font-normal">
								<span class="truncate" title={a.name ?? a.code}>{a.name ?? a.code}</span>
								<span class="shrink-0 code text-muted-foreground">{a.code}</span>
							</Label>
						</div>
					{/each}
					{#if s.allergens.length}
						<Select.Root
							type="single"
							value={s.strictness}
							onValueChange={(v) => update((p) => p.set('strictness', v))}
						>
							<Select.Trigger class="mt-1 w-full" aria-label="How strict">
								{strictnessLabel[s.strictness]}
							</Select.Trigger>
							<Select.Content>
								{#each Object.entries(strictnessLabel) as [value, label] (value)}
									<Select.Item {value} {label} />
								{/each}
							</Select.Content>
						</Select.Root>
					{/if}
				</fieldset>

				<div class="space-y-1.5 border-t pt-4">
					<Label for="category">Category</Label>
					<Select.Root
						type="single"
						value={s.category || ALL}
						onValueChange={(v) =>
							update((p) => (v === ALL ? p.delete('category') : p.set('category', v)))}
					>
						<Select.Trigger id="category" class="w-full">
							{#if s.category}<span class="code">{s.category}</span>{:else}Any category{/if}
						</Select.Trigger>
						<Select.Content class="max-h-80">
							<Select.Item value={ALL} label="Any category" />
							{#each categories as c (c.code)}
								<Select.Item value={c.code} label={c.code}>
									<span class="code">{c.code}</span>
									<span class="ml-auto pl-4 text-xs text-muted-foreground"
										>{count.format(c.productCount)}</span
									>
								</Select.Item>
							{/each}
						</Select.Content>
					</Select.Root>
					<p class="text-xs text-muted-foreground">Category names aren’t in the source data yet.</p>
				</div>
			</div>
		{/if}

		{#if filtered}
			<Button href={resolve('catalog')} variant="ghost" size="sm" class="w-full">
				<XIcon /> Clear search and filters
			</Button>
		{/if}
	</aside>

	<section class="min-w-0" aria-labelledby="results-heading">
		{#if data.error}
			<Alert.Root variant="destructive">
				<CircleAlertIcon />
				<Alert.Title>The catalog couldn’t be loaded</Alert.Title>
				<Alert.Description>
					{data.error.message}
					<span class="code text-xs">{data.error.code}</span>
				</Alert.Description>
			</Alert.Root>
		{:else if data.results}
			<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2 px-1">
				<h2 id="results-heading" class="text-sm">
					<span class="font-semibold tabular">{count.format(data.results.total)}</span>
					<span class="text-muted-foreground">
						{data.results.total === 1 ? 'product' : 'products'}{s.q ? ` for “${s.q}”` : ''}</span
					>
				</h2>
				<p class="text-xs text-muted-foreground">
					{data.results.provenance.source}, snapshot {data.results.provenance.catalogSnapshotDate}
				</p>
			</div>

			{#if data.results.items.length === 0}
				<Empty.Root class="rounded-xl border border-dashed">
					<Empty.Header>
						<Empty.Media variant="icon"><PackageSearchIcon /></Empty.Media>
						<Empty.Title>No products match</Empty.Title>
						<Empty.Description>Try fewer filters, or another word for it.</Empty.Description>
					</Empty.Header>
				</Empty.Root>
			{:else}
				<div
					class={[
						'overflow-hidden rounded-xl border bg-card shadow-xs transition-opacity',
						loading && 'opacity-60'
					]}
				>
					<Table.Root class="min-w-[50rem]">
						<Table.Header>
							<Table.Row class="bg-muted/50 hover:bg-muted/50">
								<Table.Head class="pl-5">Product</Table.Head>
								<Table.Head>Claims</Table.Head>
								{#if s.allergens.length}<Table.Head>Allergens</Table.Head>{/if}
								<Table.Head class="text-right">Reliability</Table.Head>
								<Table.Head class="pr-5 text-right">CO₂e/kg</Table.Head>
							</Table.Row>
						</Table.Header>
						<Table.Body>
							{#each data.results.items as p (p.code)}
								{@const freeFrom = p.claims.filter((c) => c.type === 'FREE_FROM')}
								<Table.Row class="group relative">
									<Table.Cell class="max-w-[26rem] py-3 pl-5 whitespace-normal">
										<a
											href={resolve(`catalog/${p.code}`)}
											class="font-medium text-balance group-hover:text-primary after:absolute after:inset-0"
											>{p.name ?? 'Unnamed product'}</a
										>
										<p class="mt-0.5 flex flex-wrap gap-x-2 text-xs text-muted-foreground">
											<span class="code">{p.code}</span>
											<span>{p.brand ?? p.vendor}</span>
											<span>sold per {p.salesUnit}</span>
										</p>
									</Table.Cell>
									<Table.Cell class="py-3 whitespace-normal">
										<div class="flex max-w-[16rem] flex-wrap gap-1">
											{#each freeFrom.slice(0, 3) as c (c.element)}
												<Badge variant="outline" class="font-normal lowercase">
													no {c.element.replaceAll('_', ' ')}
												</Badge>
											{:else}
												<span class="text-xs text-muted-foreground">—</span>
											{/each}
											{#if freeFrom.length > 3}
												<Badge variant="secondary" class="font-normal">+{freeFrom.length - 3}</Badge
												>
											{/if}
										</div>
									</Table.Cell>
									{#if s.allergens.length}
										<Table.Cell class="py-3 whitespace-normal">
											<div class="flex flex-wrap gap-1">
												{#each p.allergens.filter( (a) => s.allergens.includes(a.code) ) as a (a.code)}
													<span
														class={[
															'inline-flex h-5 items-center rounded-full px-2 text-xs whitespace-nowrap ring-1 ring-inset',
															statusTone[a.status] ?? 'bg-muted text-muted-foreground ring-border'
														]}
														title="{allergenName.get(a.code)}: {a.status
															.toLowerCase()
															.replace('_', ' ')}"
													>
														{a.code} · {a.status === 'UNKNOWN'
															? 'no data'
															: a.status.toLowerCase().replace('_', ' ')}
													</span>
												{/each}
											</div>
										</Table.Cell>
									{/if}
									<Table.Cell class="py-3 text-right tabular">
										{#if p.deliveryReliability === null}
											<span
												class="text-xs text-muted-foreground"
												title="No history, not the same as unreliable">no history</span
											>
										{:else}
											{percent(p.deliveryReliability)}
										{/if}
									</Table.Cell>
									<Table.Cell class="py-3 pr-5 text-right tabular">
										{p.carbonFootprint ? number(p.carbonFootprint.value) : '—'}
									</Table.Cell>
								</Table.Row>
							{/each}
						</Table.Body>
					</Table.Root>
				</div>

				{#if pages > 1}
					<nav class="mt-4 flex items-center justify-between gap-3" aria-label="Pages">
						<p class="text-xs text-muted-foreground tabular">
							Page {s.page} of {count.format(pages)}
						</p>
						<div class="flex gap-2">
							<Button
								variant="outline"
								size="sm"
								href={s.page > 1 ? pageHref(s.page - 1) : undefined}
								disabled={s.page <= 1}
								data-sveltekit-noscroll
							>
								<ChevronLeftIcon /> Previous
							</Button>
							<Button
								variant="outline"
								size="sm"
								href={s.page < pages ? pageHref(s.page + 1) : undefined}
								disabled={s.page >= pages}
								data-sveltekit-noscroll
							>
								Next <ChevronRightIcon />
							</Button>
						</div>
					</nav>
				{/if}
			{/if}
		{/if}
	</section>
</div>
