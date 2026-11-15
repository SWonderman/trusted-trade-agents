<script lang="ts">
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import InfoIcon from '@lucide/svelte/icons/info';
	import type { PolicyReason, ReasonSeverity } from '#lib/api/types.js';
	import { outcomeLabel } from '#lib/format.js';

	let { reasons }: { reasons: PolicyReason[] } = $props();

	const rank: Record<ReasonSeverity, number> = {
		REJECT: 0,
		NEEDS_HUMAN: 1,
		AUTO_APPROVE: 2,
		INFO: 3
	};
	const look = {
		REJECT: { icon: CircleXIcon, cls: 'text-stop' },
		NEEDS_HUMAN: { icon: CircleAlertIcon, cls: 'text-hold' },
		AUTO_APPROVE: { icon: CircleCheckIcon, cls: 'text-ok' },
		INFO: { icon: InfoIcon, cls: 'text-muted-foreground' }
	} as const;
	let sorted = $derived(reasons.toSorted((a, b) => rank[a.severity] - rank[b.severity]));

	const factLabel = (k: string) => k.replace(/([A-Z])/g, ' $1').toLowerCase();
	const factValue = (k: string, v: unknown) =>
		typeof v === 'number' && /total|limit|upto|cap|price/i.test(k)
			? new Intl.NumberFormat('en-IE', {
					style: 'currency',
					currency: 'EUR',
					maximumFractionDigits: 0
				}).format(v)
			: typeof v === 'object' && v !== null
				? JSON.stringify(v)
				: String(v);
</script>

{#if sorted.length === 0}
	<p class="text-sm text-muted-foreground">
		Every rule in the mandate passed. Nothing needed a person.
	</p>
{:else}
	<ul class="divide-y">
		{#each sorted as reason (reason.code + (reason.lineRef ?? ''))}
			{@const l = look[reason.severity]}
			<li class="grid grid-cols-[1.25rem_1fr] gap-x-3 py-3.5 first:pt-0 last:pb-0">
				<l.icon class={['mt-0.5 size-4', l.cls]} aria-hidden="true" />
				<div class="min-w-0">
					<p class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
						<span class="code font-medium">{reason.code}</span>
						{#if reason.lineRef}
							<span class="text-xs text-muted-foreground">line {reason.lineRef}</span>
						{/if}
						<span class={['ml-auto text-xs', l.cls]}>{outcomeLabel[reason.severity]}</span>
					</p>
					<p class="mt-0.5 text-sm text-pretty">{reason.message}</p>
					{#if Object.keys(reason.facts).length}
						<p class="mt-1 text-xs text-muted-foreground">
							{#each Object.entries(reason.facts) as [k, v], i (k)}
								{#if i}<span class="mx-1.5" aria-hidden="true">·</span>{/if}
								{factLabel(k)}
								<span class="font-medium text-foreground tabular">{factValue(k, v)}</span>
							{/each}
						</p>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
{/if}
