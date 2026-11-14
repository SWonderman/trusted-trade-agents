<script lang="ts">
	import { resolve } from '$app/paths';
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import InboxIcon from '@lucide/svelte/icons/inbox';
	import OutcomeBadge from '#lib/components/app/OutcomeBadge.svelte';
	import PageHeader from '#lib/components/app/PageHeader.svelte';
	import * as Empty from '#lib/components/ui/empty/index.js';
	import * as Table from '#lib/components/ui/table/index.js';
	import * as Tabs from '#lib/components/ui/tabs/index.js';
	import { moneyWhole, relative, statusLabel, statusTone } from '#lib/format.js';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	type View = 'waiting' | 'decided' | 'all';
	let view = $state<View>('waiting');

	let waiting = $derived(data.orders.filter((o) => o.status === 'PENDING_APPROVAL'));
	let decided = $derived(data.orders.filter((o) => o.status !== 'PENDING_APPROVAL'));
	let rows = $derived(view === 'waiting' ? waiting : view === 'decided' ? decided : data.orders);
	let selected = $derived(page.params.orderId ?? null);

	// After a decision the server sends ?done=ORD-0142:PLACED; say so once, then tidy the URL.
	$effect(() => {
		const done = page.url.searchParams.get('done');
		if (!done) return;
		const [orderId, status] = done.split(':');
		if (status === 'PLACED') {
			toast.success(`${orderId} approved and placed`, {
				description: 'The agent sees it on its next status check.'
			});
		} else {
			toast(`${orderId} rejected`, {
				description: 'The agent sees the rejection and your note on its next status check.'
			});
		}
		const url = new URL(page.url.href);
		url.searchParams.delete('done');
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- same page, only drops ?done
		replaceState(url, page.state);
	});
</script>

<svelte:head><title>Approvals · Saint Elmo</title></svelte:head>

<PageHeader
	title="Approvals"
	source={data.source}
	description="Orders your agents placed that their mandate sent to a person. Nothing is ordered until you approve it."
/>

<Tabs.Root bind:value={view} class="mb-4">
	<Tabs.List>
		<Tabs.Trigger value="waiting">
			Waiting for you
			{#if waiting.length}<span
					class="rounded-full bg-hold/15 px-1.5 text-xs font-semibold text-hold tabular"
					>{waiting.length}</span
				>{/if}
		</Tabs.Trigger>
		<Tabs.Trigger value="decided">Decided</Tabs.Trigger>
		<Tabs.Trigger value="all">All</Tabs.Trigger>
	</Tabs.List>
</Tabs.Root>

{#if rows.length === 0}
	<Empty.Root class="rounded-xl border border-dashed bg-card/50">
		<Empty.Header>
			<Empty.Media variant="icon"><InboxIcon /></Empty.Media>
			<Empty.Title
				>{view === 'waiting' ? 'Nothing is waiting for you' : 'No orders yet'}</Empty.Title
			>
			<Empty.Description>
				Agents are working within their mandates. New approvals appear here within seconds.
			</Empty.Description>
		</Empty.Header>
	</Empty.Root>
{:else}
	<div class="overflow-hidden rounded-xl border bg-card">
		<Table.Root class="min-w-[52rem]">
			<Table.Header>
				<Table.Row class="hover:bg-transparent">
					<Table.Head class="pl-5">Order</Table.Head>
					<Table.Head>What was asked</Table.Head>
					<Table.Head>Why it’s here</Table.Head>
					<Table.Head class="text-right">Total</Table.Head>
					<Table.Head>Status</Table.Head>
					<Table.Head class="w-10"><span class="sr-only">Open</span></Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each rows as o (o.orderId)}
					<Table.Row
						class={['group relative', selected === o.orderId && 'bg-accent/60 hover:bg-accent/60']}
					>
						<Table.Cell class="py-3.5 pl-5">
							<!-- Stretched over the whole row, so any click on it opens the order. -->
							<a
								href={resolve(`inbox/${o.orderId}`)}
								data-sveltekit-noscroll
								class="code font-medium outline-none after:absolute after:inset-0 after:rounded-sm focus-visible:after:ring-2 focus-visible:after:ring-ring"
								>{o.orderId}</a
							>
							<p class="mt-0.5 text-xs text-muted-foreground">
								<span class="code">{o.agentName}</span> · {relative(o.createdAt)}
							</p>
						</Table.Cell>
						<Table.Cell class="max-w-[22rem] py-3.5">
							<p class="truncate text-sm">{o.buyerRequest ?? '—'}</p>
						</Table.Cell>
						<Table.Cell class="py-3.5">
							{#if o.topReason}
								<span class="code text-xs text-hold">{o.topReason}</span>
								{#if o.moreReasons}<span class="ml-1 text-xs text-muted-foreground"
										>+{o.moreReasons}</span
									>{/if}
							{:else}
								<span class="text-xs text-muted-foreground">Within the mandate</span>
							{/if}
						</Table.Cell>
						<Table.Cell class="py-3.5 text-right font-medium tabular"
							>{moneyWhole(o.total)}</Table.Cell
						>
						<Table.Cell class="py-3.5">
							<OutcomeBadge outcome={statusTone[o.status]} label={statusLabel[o.status]} />
						</Table.Cell>
						<Table.Cell class="py-3.5 pr-4">
							<ChevronRightIcon
								class="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5"
								aria-hidden="true"
							/>
						</Table.Cell>
					</Table.Row>
				{/each}
			</Table.Body>
		</Table.Root>
	</div>
{/if}

{@render children()}
