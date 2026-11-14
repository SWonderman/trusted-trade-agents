<script lang="ts">
	import { resolve } from '$app/paths';
	import type { AuditEvent } from '#lib/api/types.js';
	import { date, time } from '#lib/format.js';
	import OutcomeBadge from '../ui/OutcomeBadge.svelte';

	let {
		events,
		showOrganisation = false,
		linkOrders = true
	}: { events: AuditEvent[]; showOrganisation?: boolean; linkOrders?: boolean } = $props();

	let days = $derived.by(() => {
		const groups: { day: string; events: AuditEvent[] }[] = [];
		for (const e of events) {
			const day = date(e.at);
			if (groups.at(-1)?.day !== day) groups.push({ day, events: [] });
			groups.at(-1)!.events.push(e);
		}
		return groups;
	});

	const actorLabel = { agent: 'Agent', user: 'Person', system: 'System' } as const;
</script>

<div class="space-y-8">
	{#each days as group (group.day)}
		<section aria-label={group.day}>
			<h3
				class="sticky top-14 z-[1] -mx-1 mb-2 bg-surface/95 px-1 py-1 text-xs font-semibold text-muted backdrop-blur"
			>
				{group.day}
			</h3>
			<ol class="relative">
				{#each group.events as e (e.id)}
					<li
						class="event grid grid-cols-[4.5rem_1.25rem_1fr] gap-x-2 sm:grid-cols-[5.5rem_1.5rem_1fr]"
					>
						<time datetime={e.at} class="tabular pt-0.5 text-right text-xs text-muted"
							>{time(e.at)}</time
						>
						<span class="rail" aria-hidden="true">
							<span class={['marker', e.actor.kind]}></span>
						</span>
						<div class="min-w-0 pb-5">
							<p class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm">
								<span class="sr-only">{actorLabel[e.actor.kind]}</span>
								<span
									class={[
										'font-semibold',
										e.actor.kind === 'agent' ? 'code text-lapis' : 'text-ink'
									]}
								>
									{e.actor.name}
								</span>
								<span class="code text-xs text-muted">{e.tool ?? e.type}</span>
								{#if showOrganisation}<span class="text-xs text-muted">{e.organisationName}</span
									>{/if}
							</p>
							<p class="mt-0.5 text-sm text-ink">{e.summary}</p>
							{#if e.outcome || e.stateChange || e.orderId}
								<div class="mt-1.5 flex flex-wrap items-center gap-2 text-xs">
									{#if e.outcome}<OutcomeBadge outcome={e.outcome} size="sm" />{/if}
									{#each e.reasonCodes ?? [] as code (code)}
										<span class="code rounded-sm bg-sunken px-1.5 py-0.5 text-ink">{code}</span>
									{/each}
									{#if e.stateChange}
										<span class="code text-muted">
											{e.stateChange.from ?? 'new'} →
											<span class="text-ink">{e.stateChange.to}</span>
										</span>
									{/if}
									{#if e.orderId}
										{#if linkOrders}
											<a
												href={resolve(`inbox/${e.orderId}`)}
												class="code text-lapis hover:underline">{e.orderId}</a
											>
										{:else}
											<span class="code text-muted">{e.orderId}</span>
										{/if}
									{/if}
								</div>
							{/if}
							<details class="mt-1 text-xs text-faint">
								<summary class="cursor-pointer select-none hover:text-muted">Entry {e.id}</summary>
								<dl class="code mt-1 grid grid-cols-[6rem_1fr] gap-x-2 gap-y-0.5 break-all">
									<dt>hash</dt>
									<dd class="text-muted">{e.hash}</dd>
									<dt>previous</dt>
									<dd class="text-muted">{e.prevHash}</dd>
									{#if e.quoteId}<dt>quote</dt>
										<dd class="text-muted">{e.quoteId}</dd>{/if}
									<dt>recorded</dt>
									<dd class="text-muted">{e.at}</dd>
								</dl>
							</details>
						</div>
					</li>
				{/each}
			</ol>
		</section>
	{/each}
</div>

<style>
	.rail {
		position: relative;
		display: flex;
		justify-content: center;
	}
	.rail::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		width: 1px;
		background: var(--se-line);
	}
	.event:last-child .rail::before {
		bottom: auto;
		height: 0.75rem;
	}
	/* Marker shape says who acted: ring = agent, filled = person, small dot = system. */
	.marker {
		position: relative;
		margin-top: 0.3rem;
		width: 0.625rem;
		height: 0.625rem;
		border-radius: 50%;
		background: var(--se-surface);
	}
	.marker.agent {
		border: 2px solid var(--se-lapis);
	}
	.marker.user {
		background: var(--se-ink);
		box-shadow: 0 0 0 3px var(--se-surface);
	}
	.marker.system {
		margin-top: 0.45rem;
		width: 0.375rem;
		height: 0.375rem;
		background: var(--se-faint);
		box-shadow: 0 0 0 3px var(--se-surface);
	}
</style>
