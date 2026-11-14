<script lang="ts">
	import type { PolicyReason, ReasonSeverity } from '#lib/api/types.js';
	import OutcomeBadge from '../app/OutcomeBadge.svelte';

	let { reasons }: { reasons: PolicyReason[] } = $props();

	const rank: Record<ReasonSeverity, number> = {
		REJECT: 0,
		NEEDS_HUMAN: 1,
		AUTO_APPROVE: 2,
		INFO: 3
	};
	const rail: Record<ReasonSeverity, string> = {
		REJECT: 'bg-stop',
		NEEDS_HUMAN: 'bg-hold',
		AUTO_APPROVE: 'bg-ok',
		INFO: 'bg-border'
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
	<p class="text-sm text-muted-foreground">
		Every rule in the mandate passed. Nothing needed a person.
	</p>
{:else}
	<ul class="space-y-2">
		{#each sorted as reason (reason.code + (reason.lineRef ?? ''))}
			<li class="relative overflow-hidden rounded-lg border bg-card py-3 pr-4 pl-5">
				<span class={['absolute inset-y-0 left-0 w-1', rail[reason.severity]]} aria-hidden="true"
				></span>
				<div class="flex flex-wrap items-center gap-x-3 gap-y-1.5">
					<span class="code font-medium">{reason.code}</span>
					{#if reason.lineRef}
						<span class="text-xs text-muted-foreground">line {reason.lineRef.slice(1)}</span>
					{/if}
					<OutcomeBadge outcome={reason.severity} class="ml-auto" />
				</div>
				<p class="mt-1 text-sm">{reason.message}</p>
				{#if Object.keys(reason.facts).length}
					<dl class="mt-2 flex flex-wrap gap-1.5">
						{#each Object.entries(reason.facts) as [k, v] (k)}
							<div class="flex gap-1 rounded-md bg-muted px-2 py-0.5 text-xs">
								<dt class="text-muted-foreground">{factLabel(k)}</dt>
								<dd class="font-medium tabular">{factValue(k, v)}</dd>
							</div>
						{/each}
					</dl>
				{/if}
			</li>
		{/each}
	</ul>
{/if}
