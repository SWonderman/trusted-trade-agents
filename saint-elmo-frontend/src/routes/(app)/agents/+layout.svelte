<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import Icon from '#lib/components/ui/Icon.svelte';
	import OutcomeBadge from '#lib/components/ui/OutcomeBadge.svelte';
	import { claimText, moneyWhole, relative } from '#lib/format.js';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	const substitution = {
		NEVER: 'Never',
		IF_REQUIREMENTS_HOLD: 'If requirements hold',
		ALWAYS_NEEDS_APPROVAL: 'Always needs approval'
	} as const;
</script>

<svelte:head><title>Agents and mandates · Saint Elmo</title></svelte:head>

<div class="mb-6 flex flex-wrap items-end justify-between gap-4">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight text-ink">Agents and mandates</h1>
		<p class="mt-1 max-w-[62ch] text-sm text-muted">
			Each agent works for one task, under one mandate that only people here can change. An agent
			can read its mandate but never widen it.
		</p>
	</div>
	<a href={resolve('agents/new')} class="btn btn-primary"><Icon name="plus" /> New agent</a>
</div>

<div class="panel overflow-x-auto">
	<table class="w-full min-w-[56rem] text-left text-sm">
		<thead class="border-b border-line bg-surface text-xs text-muted">
			<tr>
				<th scope="col" class="px-4 py-2.5 font-medium">Agent</th>
				<th scope="col" class="px-4 py-2.5 font-medium">Spend this period</th>
				<th scope="col" class="px-4 py-2.5 font-medium">Decides alone up to</th>
				<th scope="col" class="px-4 py-2.5 font-medium">Requirements</th>
				<th scope="col" class="px-4 py-2.5 font-medium">Substitutes</th>
				<th scope="col" class="px-4 py-2.5 font-medium">Keys</th>
				<th scope="col" class="px-4 py-2.5 font-medium"><span class="sr-only">Open</span></th>
			</tr>
		</thead>
		<tbody class="divide-y divide-line">
			{#each data.agents as agent (agent.id)}
				{@const m = agent.mandate}
				{@const used = agent.periodSpend.committed / m.periodSpendCap}
				<tr
					class={[
						'align-top hover:bg-surface',
						page.params.agentId === agent.id && 'bg-lapis-wash/50'
					]}
				>
					<td class="px-4 py-3.5">
						<div class="flex items-center gap-2">
							<a
								href={resolve(`agents/${agent.id}`)}
								class="code font-semibold text-ink hover:text-lapis">{agent.name}</a
							>
							{#if agent.status === 'DISABLED'}
								<OutcomeBadge outcome="REJECT" label="Disabled" size="sm" />
							{/if}
						</div>
						<p class="mt-0.5 max-w-[30ch] text-muted">{agent.purpose}</p>
						<p class="mt-1 text-xs text-faint">
							{agent.lastActiveAt ? `Active ${relative(agent.lastActiveAt)}` : 'Not used yet'}
						</p>
					</td>
					<td class="px-4 py-3.5">
						<p class="tabular text-ink">
							{moneyWhole(agent.periodSpend.committed)}
							<span class="text-muted">of {moneyWhole(m.periodSpendCap)}</span>
						</p>
						<div
							class="mt-1.5 h-1.5 w-32 overflow-hidden rounded-full bg-sunken"
							role="meter"
							aria-valuenow={Math.round(used * 100)}
							aria-valuemin={0}
							aria-valuemax={100}
							aria-label="Share of the {m.spendPeriod === 'WEEK' ? 'weekly' : 'monthly'} cap used"
						>
							<div
								class={['h-full rounded-full', used > 0.85 ? 'bg-hold' : 'bg-lapis']}
								style:width="{Math.min(100, used * 100)}%"
							></div>
						</div>
						<p class="mt-1 text-xs text-muted">per {m.spendPeriod === 'WEEK' ? 'week' : 'month'}</p>
					</td>
					<td class="px-4 py-3.5">
						<p class="tabular text-ink">{moneyWhole(m.autoApproveUpTo)}</p>
						<p class="tabular text-xs text-muted">hard limit {moneyWhole(m.maxOrderTotal)}</p>
					</td>
					<td class="px-4 py-3.5">
						<div class="flex max-w-[22rem] flex-wrap gap-1">
							{#each m.requiredClaims as c (claimText(c))}
								<span class="code rounded-sm border border-line px-1.5 py-0.5 text-ink"
									>{claimText(c)}</span
								>
							{/each}
							{#each m.excludedAllergens as a (a)}
								<span
									class="code rounded-sm border border-stop/30 bg-stop-wash px-1.5 py-0.5 text-stop"
									title="Excluded allergen"
								>
									no {a}
								</span>
							{/each}
							{#if m.allowedCategoryCodes.length}
								<span class="rounded-sm bg-sunken px-1.5 py-0.5 text-xs text-muted">
									{m.allowedCategoryCodes.length} categories only
								</span>
							{/if}
							{#if !m.requiredClaims.length && !m.excludedAllergens.length && !m.allowedCategoryCodes.length}
								<span class="text-muted">Any product</span>
							{/if}
						</div>
					</td>
					<td class="px-4 py-3.5 text-ink">{substitution[m.substitutionPolicy]}</td>
					<td class="tabular px-4 py-3.5 text-ink">
						{agent.activeKeys}
						<span class="text-muted">active</span>
					</td>
					<td class="px-4 py-3.5 text-right">
						<a
							href={resolve(`agents/${agent.id}`)}
							class="btn btn-sm"
							aria-label="Open {agent.name}"
						>
							Open <Icon name="chevronRight" size={14} />
						</a>
					</td>
				</tr>
			{:else}
				<tr>
					<td colspan="7" class="px-4 py-10 text-center">
						<p class="font-semibold text-ink">No agents yet</p>
						<p class="mt-1 text-sm text-muted">Create one, set its mandate, then give it a key.</p>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

{@render children()}
