<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import DownloadIcon from '@lucide/svelte/icons/download';
	import ScrollTextIcon from '@lucide/svelte/icons/scroll-text';
	import SearchIcon from '@lucide/svelte/icons/search';
	import XIcon from '@lucide/svelte/icons/x';
	import AuditTimeline from '#lib/components/domain/AuditTimeline.svelte';
	import PageHeader from '#lib/components/app/PageHeader.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Empty from '#lib/components/ui/empty/index.js';
	import * as InputGroup from '#lib/components/ui/input-group/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { outcomeLabel } from '#lib/format.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let filtered = $derived(
		Boolean(data.filter.agentId || data.filter.orderId || data.filter.type || data.filter.outcome)
	);
	const ALL = '__all';
	const outcomes = ['AUTO_APPROVE', 'NEEDS_HUMAN', 'REJECT'] as const;

	/** Filters live in the URL, so a filtered view can be linked and shared. */
	function setFilter(key: string, value: string | undefined) {
		const url = new URL(page.url.href);
		if (value && value !== ALL) url.searchParams.set(key, value);
		else url.searchParams.delete(key);
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- same resolved route, new query only
		goto(`${resolve('audit')}${url.search}`, { reset: false });
	}
	let order = $derived(data.filter.orderId ?? '');
</script>

<svelte:head><title>Audit trail · Saint Elmo</title></svelte:head>

<PageHeader
	title="Audit trail"
	source={data.source}
	description="Every tool call, policy decision, approval and token change, newest first. Entries are only ever added, and each carries the hash of the one before, so edited history can be detected. {data.crossCustomer
		? 'You are seeing every buyer organisation.'
		: 'Valio Aimo sees the same entries.'}"
>
	{#snippet actions()}
		<Button
			variant="outline"
			href="{resolve('audit/export.json')}{page.url.search}"
			download
			data-sveltekit-reload
		>
			<DownloadIcon /> Download JSON
		</Button>
	{/snippet}
</PageHeader>

<div class="grid items-start gap-6 lg:grid-cols-[17rem_1fr]">
	<form
		method="GET"
		class="space-y-4 rounded-xl border bg-card p-4 lg:sticky lg:top-20"
		data-sveltekit-keepfocus
		onsubmit={(e) => {
			e.preventDefault();
			setFilter('order', order.trim() || undefined);
		}}
	>
		<p class="text-sm font-medium">Filter</p>
		<div class="space-y-1.5">
			<Label for="f-order">Order or quote</Label>
			<InputGroup.Root>
				<InputGroup.Addon><SearchIcon /></InputGroup.Addon>
				<InputGroup.Input
					id="f-order"
					name="order"
					class="code"
					placeholder="Order id, a UUID"
					bind:value={order}
				/>
			</InputGroup.Root>
		</div>
		<div class="space-y-1.5">
			<Label for="f-agent">Agent</Label>
			<Select.Root
				type="single"
				value={data.filter.agentId ?? ALL}
				onValueChange={(v) => setFilter('agent', v)}
			>
				<Select.Trigger id="f-agent" class="w-full">
					{data.agentOptions.find((a) => a.id === data.filter.agentId)?.name ?? 'All agents'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value={ALL} label="All agents" />
					{#each data.agentOptions as a (a.id)}
						<Select.Item value={a.id} label={a.name} class="code" />
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		<div class="space-y-1.5">
			<Label for="f-type">Tool call or event</Label>
			<Select.Root
				type="single"
				value={data.filter.type ?? ALL}
				onValueChange={(v) => setFilter('type', v)}
			>
				<Select.Trigger id="f-type" class="w-full">
					<span class={data.filter.type && 'code'}>{data.filter.type ?? 'Everything'}</span>
				</Select.Trigger>
				<Select.Content>
					<Select.Item value={ALL} label="Everything" />
					{#each data.typeOptions as t (t)}
						<Select.Item value={t} label={t} class="code" />
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		<div class="space-y-1.5">
			<Label for="f-outcome">Policy outcome</Label>
			<Select.Root
				type="single"
				value={data.filter.outcome ?? ALL}
				onValueChange={(v) => setFilter('outcome', v)}
			>
				<Select.Trigger id="f-outcome" class="w-full">
					{data.filter.outcome ? outcomeLabel[data.filter.outcome] : 'Any'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value={ALL} label="Any" />
					{#each outcomes as o (o)}
						<Select.Item value={o} label={outcomeLabel[o]} />
					{/each}
				</Select.Content>
			</Select.Root>
		</div>
		{#if filtered}
			<Button href={resolve('audit')} variant="ghost" size="sm" class="w-full">
				<XIcon /> Clear filters
			</Button>
		{/if}
		<p class="border-t pt-3 text-xs text-muted-foreground tabular">
			{filtered
				? `${data.events.length} of ${data.total} entries`
				: `${data.events.length} entries`}
		</p>
	</form>

	{#if data.events.length === 0}
		<Empty.Root class="rounded-xl border border-dashed">
			<Empty.Header>
				<Empty.Media variant="icon"><ScrollTextIcon /></Empty.Media>
				<Empty.Title>No entries match these filters</Empty.Title>
				<Empty.Description
					>Check the order id, or clear the filters to see the whole trail.</Empty.Description
				>
			</Empty.Header>
			<Empty.Content>
				<Button href={resolve('audit')} variant="outline">Clear filters</Button>
			</Empty.Content>
		</Empty.Root>
	{:else}
		<!-- On large screens the trail scrolls inside its card, sized to what is left of the screen
		     under the page header (sticky covers a header that wraps taller).
		     The padding sits inside the scroller so day headings stick flush to its top edge. -->
		<div
			class="min-w-0 rounded-xl border bg-card lg:sticky lg:top-20 lg:max-h-[calc(100dvh-18rem)] lg:overflow-y-auto lg:overscroll-contain"
			{@attach (el) => {
				// A new filter starts the trail back at its newest entry
				void data.events;
				el.scrollTop = 0;
			}}
		>
			<div class="px-3 py-5 sm:px-6">
				<AuditTimeline
					contained
					events={data.events}
					showOrganisation={data.crossCustomer}
					linkOrders={!data.crossCustomer}
				/>
			</div>
		</div>
	{/if}
</div>
