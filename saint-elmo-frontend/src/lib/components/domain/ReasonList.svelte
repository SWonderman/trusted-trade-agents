<script lang="ts">
	import type { PolicyReason, ReasonSeverity } from '#lib/api/types.js';
	import OutcomeBadge from '../ui/OutcomeBadge.svelte';

	let { reasons }: { reasons: PolicyReason[] } = $props();

	const rank: Record<ReasonSeverity, number> = {
		REJECT: 0,
		NEEDS_HUMAN: 1,
		AUTO_APPROVE: 2,
		INFO: 3
	};
	let sorted = $derived(reasons.toSorted((a, b) => rank[a.severity] - rank[b.severity]));

	const factLabel = (k: string) => k.replace(/([A-Z])/g, ' $1').toLowerCase();
	const factValue = (k: string, v: unknown) =>
		typeof v === 'number' && /total|limit|upto|cap|price/i.test(k)
			? new Intl.NumberFormat('en-IE', {
					style: 'currency',
					currency: 'EUR',
					maximumFractionDigits: 0
				}).format(v)
			: String(v);
</script>

{#if sorted.length === 0}
	<p class="text-sm text-muted">Every rule in the mandate passed. Nothing needed a person.</p>
{:else}
	<ul class="divide-y divide-line">
		{#each sorted as reason (reason.code + (reason.lineRef ?? ''))}
			<li class="grid gap-x-3 gap-y-1.5 py-3 first:pt-0 last:pb-0 sm:grid-cols-[9.5rem_1fr]">
				<div class="flex sm:block">
					<OutcomeBadge outcome={reason.severity} size="sm" />
				</div>
				<div class="min-w-0">
					<p class="flex flex-wrap items-baseline gap-x-2">
						<span class="code font-medium text-ink">{reason.code}</span>
						{#if reason.lineRef}
							<span class="text-xs text-muted">line {reason.lineRef.slice(1)}</span>
						{/if}
					</p>
					<p class="mt-0.5 text-sm text-ink">{reason.message}</p>
					{#if Object.keys(reason.facts).length}
						<dl class="mt-1.5 flex flex-wrap gap-1.5">
							{#each Object.entries(reason.facts) as [k, v] (k)}
								<div class="flex gap-1 rounded-sm bg-sunken px-1.5 py-0.5 text-xs">
									<dt class="text-muted">{factLabel(k)}</dt>
									<dd class="tabular font-medium text-ink">{factValue(k, v)}</dd>
								</div>
							{/each}
						</dl>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
{/if}
