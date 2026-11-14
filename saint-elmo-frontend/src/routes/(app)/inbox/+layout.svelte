<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import ArrowLeftRightIcon from '@lucide/svelte/icons/arrow-left-right';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import InboxIcon from '@lucide/svelte/icons/inbox';
	import OutcomeBadge from '#lib/components/app/OutcomeBadge.svelte';
	import PageHeader from '#lib/components/app/PageHeader.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { moneyWhole, relative, statusLabel, statusTone } from '#lib/format.js';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	let selected = $derived(page.params.orderId ?? null);
	let done = $derived(page.url.searchParams.get('done'));
</script>

<svelte:head><title>Approvals · Saint Elmo</title></svelte:head>

<PageHeader
	title="Approvals"
	source={data.source}
	description="Orders your agents placed that their mandate sent to a person. Nothing here is ordered until you approve it."
/>

{#if done}
	{@const [orderId, status] = done.split(':')}
	<Alert.Root
		class={[
			'mb-6',
			status === 'PLACED' ? 'border-ok/30 bg-ok/6 text-ok' : 'border-stop/30 bg-stop/6 text-stop'
		]}
	>
		{#if status === 'PLACED'}<CircleCheckIcon />{:else}<CircleXIcon />{/if}
		<Alert.Title class="text-foreground">
			<span class="code">{orderId}</span>
			{status === 'PLACED' ? 'approved and placed' : 'rejected'}
		</Alert.Title>
		<Alert.Description class="flex flex-wrap gap-x-3">
			{status === 'PLACED'
				? 'It’s in the order book. The agent sees it on its next status check.'
				: 'The agent sees the rejection and your note on its next status check.'}
			<a
				href="{resolve('audit')}?order={orderId}"
				class="font-medium text-foreground underline underline-offset-2">See audit trail</a
			>
		</Alert.Description>
	</Alert.Root>
{/if}

<div class="grid items-start gap-6 lg:grid-cols-[22rem_1fr]">
	<section
		aria-labelledby="queue-heading"
		class={['min-w-0 lg:sticky lg:top-20', selected && 'max-lg:hidden']}
	>
		<h2 id="queue-heading" class="mb-3 flex items-center gap-2 px-1 text-sm font-medium">
			Waiting for you
			<span class="rounded-full bg-hold/12 px-2 text-xs font-semibold text-hold tabular"
				>{data.pending.length}</span
			>
		</h2>

		{#if data.pending.length === 0}
			<div class="rounded-xl border border-dashed px-5 py-10 text-center">
				<InboxIcon class="mx-auto size-6 text-muted-foreground" aria-hidden="true" />
				<p class="mt-3 font-medium">Nothing is waiting for you</p>
				<p class="mx-auto mt-1 max-w-[32ch] text-sm text-muted-foreground">
					Agents are working within their mandates. New approvals appear here within seconds.
				</p>
			</div>
		{:else}
			<ul class="space-y-2">
				{#each data.pending as o (o.orderId)}
					{@const active = selected === o.orderId}
					<li>
						<a
							href={resolve(`inbox/${o.orderId}`)}
							aria-current={active ? 'page' : undefined}
							class={[
								'block rounded-xl border bg-card px-4 py-3.5 shadow-xs transition-[border-color,box-shadow] hover:border-primary/30',
								active && 'border-primary/50 ring-3 ring-primary/10'
							]}
						>
							<div class="flex items-baseline justify-between gap-3">
								<span class="code font-medium">{o.orderId}</span>
								<span class="font-semibold tabular">{moneyWhole(o.total)}</span>
							</div>
							<p class="mt-1 line-clamp-2 text-sm text-muted-foreground">{o.buyerRequest}</p>
							<div class="mt-2.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-xs">
								<span class="code text-primary">{o.agentName}</span>
								{#if o.topReason}<span class="code text-hold">{o.topReason}</span>{/if}
								{#if o.reasonCount > 1}<span class="text-muted-foreground"
										>+{o.reasonCount - 1}</span
									>{/if}
								{#if o.hasSubstitute}
									<ArrowLeftRightIcon
										class="size-3.5 text-muted-foreground"
										aria-label="Has a substitute"
									/>
								{/if}
								<span class="ml-auto text-muted-foreground">{relative(o.createdAt)}</span>
							</div>
						</a>
					</li>
				{/each}
			</ul>
		{/if}

		{#if data.recent.length}
			<h2 class="mt-8 mb-2 px-1 text-sm font-medium">Recently decided</h2>
			<ul class="divide-y rounded-xl border bg-card">
				{#each data.recent as o (o.orderId)}
					<li>
						<a
							href={resolve(`inbox/${o.orderId}`)}
							class="flex items-center gap-3 px-3.5 py-2.5 text-sm first:rounded-t-xl last:rounded-b-xl hover:bg-muted/60"
						>
							<span class="code">{o.orderId}</span>
							<span class="truncate text-muted-foreground">{o.agentName}</span>
							<OutcomeBadge
								outcome={statusTone[o.status]}
								label={statusLabel[o.status]}
								class="ml-auto"
							/>
						</a>
					</li>
				{/each}
			</ul>
		{/if}
	</section>

	<div class={['min-w-0', !selected && 'max-lg:hidden']}>
		{@render children()}
	</div>
</div>
