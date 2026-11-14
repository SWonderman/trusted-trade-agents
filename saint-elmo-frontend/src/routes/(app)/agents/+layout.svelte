<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import BotIcon from '@lucide/svelte/icons/bot';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import OutcomeBadge from '#lib/components/app/OutcomeBadge.svelte';
	import PageHeader from '#lib/components/app/PageHeader.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Empty from '#lib/components/ui/empty/index.js';
	import { Progress } from '#lib/components/ui/progress/index.js';
	import * as Table from '#lib/components/ui/table/index.js';
	import { claimText, moneyWhole, relative } from '#lib/format.js';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	const substitution = {
		NEVER: 'Never',
		IF_REQUIREMENTS_HOLD: 'If requirements hold',
		ALWAYS_NEEDS_APPROVAL: 'Always ask a person'
	} as const;
</script>

<svelte:head><title>Agents & mandates · Saint Elmo</title></svelte:head>

<PageHeader
	title="Agents & mandates"
	source={data.source}
	description="Each agent works on one task, under one mandate that only people here can change. An agent can read its mandate but never widen it."
>
	{#snippet actions()}
		<Button href={resolve('agents/new')}><PlusIcon /> New agent</Button>
	{/snippet}
</PageHeader>

{#if data.agents.length === 0}
	<Empty.Root class="rounded-xl border border-dashed">
		<Empty.Header>
			<Empty.Media variant="icon"><BotIcon /></Empty.Media>
			<Empty.Title>No agents yet</Empty.Title>
			<Empty.Description
				>Create one, set its mandate, then issue it an Agent token.</Empty.Description
			>
		</Empty.Header>
		<Empty.Content>
			<Button href={resolve('agents/new')}><PlusIcon /> New agent</Button>
		</Empty.Content>
	</Empty.Root>
{:else}
	<div class="overflow-hidden rounded-xl border bg-card shadow-xs">
		<Table.Root class="min-w-[58rem]">
			<Table.Header>
				<Table.Row class="bg-muted/50 hover:bg-muted/50">
					<Table.Head class="pl-5">Agent</Table.Head>
					<Table.Head>Spend this period</Table.Head>
					<Table.Head>Decides alone up to</Table.Head>
					<Table.Head>Requirements</Table.Head>
					<Table.Head>Substitutes</Table.Head>
					<Table.Head class="text-right">Tokens</Table.Head>
					<Table.Head class="w-12"><span class="sr-only">Open</span></Table.Head>
				</Table.Row>
			</Table.Header>
			<Table.Body>
				{#each data.agents as agent (agent.id)}
					{@const m = agent.mandate}
					{@const used = Math.min(100, (agent.periodSpend.committed / m.periodSpendCap) * 100)}
					<Table.Row
						class={['group relative align-top', page.params.agentId === agent.id && 'bg-accent/50']}
					>
						<Table.Cell class="py-4 pl-5">
							<div class="flex items-center gap-2">
								<a
									href={resolve(`agents/${agent.id}`)}
									class="code font-semibold text-foreground after:absolute after:inset-0 hover:text-primary"
									>{agent.name}</a
								>
								{#if agent.status === 'DISABLED'}
									<OutcomeBadge outcome="REJECT" label="Disabled" />
								{/if}
							</div>
							<p class="mt-1 max-w-[30ch] text-sm whitespace-normal text-muted-foreground">
								{agent.purpose}
							</p>
							<p class="mt-1.5 text-xs text-muted-foreground/80">
								{agent.lastActiveAt ? `Active ${relative(agent.lastActiveAt)}` : 'Not used yet'}
							</p>
						</Table.Cell>
						<Table.Cell class="py-4">
							<p class="tabular">
								{moneyWhole(agent.periodSpend.committed)}
								<span class="text-muted-foreground">/ {moneyWhole(m.periodSpendCap)}</span>
							</p>
							<Progress
								value={used}
								class={[
									'mt-2 h-1.5 w-32',
									used > 85 && '[&>[data-slot=progress-indicator]]:bg-hold'
								]}
								aria-label="Share of the {m.spendPeriod === 'WEEK' ? 'weekly' : 'monthly'} cap used"
							/>
							<p class="mt-1.5 text-xs text-muted-foreground">
								per {m.spendPeriod === 'WEEK' ? 'week' : 'month'}
							</p>
						</Table.Cell>
						<Table.Cell class="py-4">
							<p class="tabular">{moneyWhole(m.autoApproveUpTo)}</p>
							<p class="text-xs text-muted-foreground tabular">
								limit {moneyWhole(m.maxOrderTotal)}
							</p>
						</Table.Cell>
						<Table.Cell class="py-4">
							<div class="flex max-w-[22rem] flex-wrap gap-1">
								{#each m.requiredClaims as c (claimText(c))}
									<Badge variant="outline" class="code font-normal">{claimText(c)}</Badge>
								{/each}
								{#each m.excludedAllergens as a (a)}
									<Badge variant="destructive" class="code font-normal" title="Excluded allergen"
										>no {a}</Badge
									>
								{/each}
								{#if m.allowedCategoryCodes.length}
									<Badge variant="secondary" class="font-normal">
										{m.allowedCategoryCodes.length} categories only
									</Badge>
								{/if}
								{#if !m.requiredClaims.length && !m.excludedAllergens.length && !m.allowedCategoryCodes.length}
									<span class="text-muted-foreground">Any product</span>
								{/if}
							</div>
						</Table.Cell>
						<Table.Cell class="py-4">{substitution[m.substitutionPolicy]}</Table.Cell>
						<Table.Cell class="py-4 text-right tabular">
							{agent.activeKeys}
							<span class="text-muted-foreground">active</span>
						</Table.Cell>
						<Table.Cell class="py-4 pr-4">
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
