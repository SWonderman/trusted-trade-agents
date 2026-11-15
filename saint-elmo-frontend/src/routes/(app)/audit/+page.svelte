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
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import type { AuditEventPage } from '#lib/api/types.js';
	import { localDay, startOfLocalDay } from '#lib/format.js';
	import { isFiltered } from './filter.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let filtered = $derived(isFiltered(data.filter));
	const ALL = '__all';

	// The first page comes with the load; "load more" appends older pages until a new filter.
	let events = $derived(data.page.items);
	let nextCursor = $derived(data.page.nextCursor);
	let loading = $state(false);
	let loadError = $state(false);

	async function loadMore() {
		if (!nextCursor) return;
		loading = true;
		loadError = false;
		try {
			const url = new URL(page.url.href);
			url.searchParams.set('cursor', nextCursor);
			const res = await fetch(`${resolve('audit/events.json')}${url.search}`);
			if (!res.ok) throw new Error(String(res.status));
			const more: AuditEventPage = await res.json();
			events = [...events, ...more.items];
			nextCursor = more.nextCursor;
		} catch {
			loadError = true;
		} finally {
			loading = false;
		}
	}

	/** Filters live in the URL, so a filtered view can be linked and shared. */
	function setFilter(key: string, value: string | undefined) {
		const url = new URL(page.url.href);
		if (value && value !== ALL) url.searchParams.set(key, value);
		else url.searchParams.delete(key);
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- same resolved route, new query only
		goto(`${resolve('audit')}${url.search}`, { reset: false });
	}
	let subject = $derived(data.filter.subject ?? '');
</script>

<svelte:head><title>Audit trail · Saint Elmo</title></svelte:head>

<PageHeader
	title="Audit trail"
	source={data.source}
	description="Every quote, order, policy decision, approval and change to an agent’s authority, newest first. Entries are only ever added; lookups such as searches and price checks aren’t recorded. {data.crossCustomer
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
			setFilter('subject', subject.trim() || undefined);
		}}
	>
		<p class="text-sm font-medium">Filter</p>
		<div class="space-y-1.5">
			<Label for="f-subject">Order, quote or agent</Label>
			<InputGroup.Root>
				<InputGroup.Addon><SearchIcon /></InputGroup.Addon>
				<InputGroup.Input
					id="f-subject"
					name="subject"
					class="code"
					placeholder="Its id, a UUID"
					bind:value={subject}
				/>
			</InputGroup.Root>
		</div>
		<div class="space-y-1.5">
			<Label for="f-agent">Agent</Label>
			<Select.Root
				type="single"
				value={data.filter.agentId ?? ALL}
				onValueChange={(v) => setFilter('agentId', v)}
			>
				<Select.Trigger id="f-agent" class="w-full">
					{data.filter.agentId
						? (data.agentOptions.find((a) => a.id === data.filter.agentId)?.name ??
							data.filter.agentId)
						: 'All agents'}
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
			<Label for="f-type">Event</Label>
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
		<div class="grid gap-4">
			<div class="space-y-1.5">
				<Label for="f-from">From</Label>
				<Input
					id="f-from"
					type="date"
					value={localDay(data.filter.from)}
					max={localDay(data.filter.to, 1) || undefined}
					onchange={(e) => setFilter('from', startOfLocalDay(e.currentTarget.value))}
				/>
			</div>
			<div class="space-y-1.5">
				<Label for="f-to">To</Label>
				<!-- The backend's `to` is exclusive: the day after the last one picked. -->
				<Input
					id="f-to"
					type="date"
					value={localDay(data.filter.to, 1)}
					min={localDay(data.filter.from) || undefined}
					onchange={(e) => setFilter('to', startOfLocalDay(e.currentTarget.value, 1))}
				/>
			</div>
		</div>
		{#if filtered}
			<Button href={resolve('audit')} variant="ghost" size="sm" class="w-full">
				<XIcon /> Clear filters
			</Button>
		{/if}
		<p class="border-t pt-3 text-xs text-muted-foreground tabular">
			{events.length}
			{events.length === 1 ? 'entry' : 'entries'}{nextCursor ? ', more to load' : ''}
		</p>
	</form>

	{#if events.length === 0}
		<Empty.Root class="rounded-xl border border-dashed">
			<Empty.Header>
				<Empty.Media variant="icon"><ScrollTextIcon /></Empty.Media>
				<Empty.Title>No entries match these filters</Empty.Title>
				<Empty.Description
					>Check the id and the dates, or clear the filters to see the whole trail.</Empty.Description
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
				void data.page;
				el.scrollTop = 0;
			}}
		>
			<div class="px-3 py-5 sm:px-6">
				<AuditTimeline
					stickyDays="container"
					{events}
					showOrganisation={data.crossCustomer}
					linkOrders={!data.crossCustomer}
				/>
				{#if nextCursor}
					<div class="flex flex-col items-center gap-2 border-t pt-4">
						<Button variant="outline" size="sm" onclick={loadMore} disabled={loading}>
							{#if loading}<Spinner />Loading…{:else}Load older entries{/if}
						</Button>
						{#if loadError}
							<p role="alert" class="text-xs text-stop">
								Couldn’t load more entries. Try again in a moment.
							</p>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
