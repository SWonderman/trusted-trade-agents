<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { moneyWhole, relative, statusLabel, statusTone } from '#lib/format.js';
	import OutcomeBadge from '#lib/components/ui/OutcomeBadge.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	let selected = $derived(page.params.orderId ?? null);
	let done = $derived(page.url.searchParams.get('done'));
</script>

<svelte:head><title>Approval inbox · Saint Elmo</title></svelte:head>

<div class="mb-6 flex flex-wrap items-end justify-between gap-4">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight text-ink">Approval inbox</h1>
		<p class="mt-1 max-w-[60ch] text-sm text-muted">
			Orders your agents placed that the mandate sent to a person. Nothing here is ordered until you
			approve it.
		</p>
	</div>
</div>

{#if done}
	{@const [orderId, status] = done.split(':')}
	<p
		role="status"
		class={[
			'mb-5 flex items-center gap-2 rounded-md border px-4 py-3 text-sm',
			status === 'PLACED'
				? 'border-ok/30 bg-ok-wash text-ok'
				: 'border-stop/30 bg-stop-wash text-stop'
		]}
	>
		<Icon name={status === 'PLACED' ? 'check' : 'ban'} />
		<span>
			<span class="code font-medium">{orderId}</span>
			{status === 'PLACED'
				? 'approved and placed in the order book. The agent sees it on its next status check.'
				: 'rejected. The agent sees the rejection and your note on its next status check.'}
		</span>
		<a
			href="{resolve('audit')}?order={orderId}"
			class="ml-auto font-medium underline underline-offset-2">See audit trail</a
		>
	</p>
{/if}

<div class="grid gap-6 lg:grid-cols-[21rem_1fr]">
	<section aria-labelledby="queue-heading" class={['min-w-0', selected && 'max-lg:hidden']}>
		<h2 id="queue-heading" class="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
			Waiting for you
			<span class="tabular rounded-full bg-sunken px-2 text-xs text-muted"
				>{data.pending.length}</span
			>
		</h2>

		{#if data.pending.length === 0}
			<div class="panel px-5 py-8 text-center">
				<p class="font-semibold text-ink">Nothing is waiting for you</p>
				<p class="mx-auto mt-1 max-w-[32ch] text-sm text-muted">
					Agents are working within their mandates. New approvals appear here within seconds.
				</p>
			</div>
		{:else}
			<ul class="panel divide-y divide-line overflow-hidden">
				{#each data.pending as o (o.orderId)}
					<li>
						<a
							href={resolve(`inbox/${o.orderId}`)}
							aria-current={selected === o.orderId ? 'page' : undefined}
							class={[
								'block border-l-[3px] px-4 py-3.5 hover:bg-surface',
								selected === o.orderId ? 'border-l-lapis bg-lapis-wash/60' : 'border-l-transparent'
							]}
						>
							<div class="flex items-baseline justify-between gap-3">
								<span class="code font-medium text-ink">{o.orderId}</span>
								<span class="tabular font-semibold text-ink">{moneyWhole(o.total)}</span>
							</div>
							<p class="mt-0.5 truncate text-sm text-muted">{o.buyerRequest}</p>
							<div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
								<span class="font-medium text-ink">{o.agentName}</span>
								{#if o.topReason}<span class="code text-hold">{o.topReason}</span>{/if}
								{#if o.reasonCount > 1}<span>+{o.reasonCount - 1} more</span>{/if}
								<span class="ml-auto">{relative(o.createdAt)}</span>
							</div>
						</a>
					</li>
				{/each}
			</ul>
		{/if}

		{#if data.recent.length}
			<h2 class="mt-8 mb-2 text-sm font-semibold text-ink">Recently decided</h2>
			<ul class="space-y-1">
				{#each data.recent as o (o.orderId)}
					<li>
						<a
							href={resolve(`inbox/${o.orderId}`)}
							class="flex items-center gap-3 rounded-sm px-2 py-1.5 text-sm hover:bg-sunken"
						>
							<span class="code text-ink">{o.orderId}</span>
							<span class="truncate text-muted">{o.agentName}</span>
							<span class="ml-auto"
								><OutcomeBadge
									outcome={statusTone[o.status]}
									label={statusLabel[o.status]}
									size="sm"
								/></span
							>
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
