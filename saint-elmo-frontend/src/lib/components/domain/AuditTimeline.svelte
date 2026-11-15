<script lang="ts">
	import { resolve } from '$app/paths';
	import BotIcon from '@lucide/svelte/icons/bot';
	import CogIcon from '@lucide/svelte/icons/cog';
	import UserIcon from '@lucide/svelte/icons/user';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import type { AuditEvent } from '#lib/api/types.js';
	import { orderOf, quoteRequest } from '#lib/audit.js';
	import { date, shortId, time } from '#lib/format.js';
	import * as Collapsible from '#lib/components/ui/collapsible/index.js';
	import OutcomeBadge from '../app/OutcomeBadge.svelte';

	type TimelineEvent = AuditEvent & { organisationName?: string };

	let {
		events,
		showOrganisation = false,
		linkOrders = true,
		stickyDays = 'page'
	}: {
		/** In the order to show them: newest first for the audit trail, oldest first for an order trail. */
		events: TimelineEvent[];
		showOrganisation?: boolean;
		linkOrders?: boolean;
		/**
		 * Where day headings stick: under the page header, or also to the top of a container
		 * that scrolls on large screens; 'none' where they shouldn't stick at all.
		 */
		stickyDays?: 'page' | 'container' | 'none';
	} = $props();

	let days = $derived.by(() => {
		const groups: { day: string; events: TimelineEvent[] }[] = [];
		for (const e of events) {
			const day = date(e.at);
			if (groups.at(-1)?.day !== day) groups.push({ day, events: [] });
			groups.at(-1)!.events.push(e);
		}
		return groups;
	});

	// Marker icon and colour say who acted: agent, person or system.
	const actor = {
		agent: { label: 'Agent', icon: BotIcon, cls: 'bg-primary/10 text-primary ring-primary/20' },
		user: { label: 'Person', icon: UserIcon, cls: 'bg-foreground text-background ring-foreground' },
		system: { label: 'System', icon: CogIcon, cls: 'bg-muted text-muted-foreground ring-border' }
	} as const;
</script>

<div class="space-y-8">
	{#each days as group (group.day)}
		<section aria-label={group.day}>
			<h3
				class={[
					'-mx-2 mb-3 px-2 py-1.5 text-xs font-medium tracking-wider text-muted-foreground uppercase',
					stickyDays !== 'none' && 'sticky top-14 z-[1] bg-card/95 backdrop-blur',
					stickyDays === 'container' && 'lg:top-0'
				]}
			>
				{group.day}
			</h3>
			<ol>
				{#each group.events as e (e.id)}
					{@const a = actor[e.actor.kind]}
					{@const order = orderOf(e)}
					{@const request = quoteRequest(e)}
					<li
						class="group/event grid grid-cols-[3.75rem_1.75rem_1fr] gap-x-3 sm:grid-cols-[4.5rem_1.75rem_1fr]"
					>
						<time datetime={e.at} class="pt-1 text-right text-xs text-muted-foreground tabular"
							>{time(e.at)}</time
						>
						<span class="relative flex justify-center" aria-hidden="true">
							<span
								class="absolute top-0 bottom-0 w-px bg-border group-last/event:bottom-auto group-last/event:h-3"
							></span>
							<span
								class={[
									'relative mt-0.5 grid size-6 place-items-center rounded-full ring-1 ring-inset',
									a.cls
								]}
							>
								<a.icon class="size-3.5" />
							</span>
						</span>
						<div class="min-w-0 pb-6">
							<p class="text-sm font-medium text-pretty">{e.summary}</p>
							{#if request?.buyerRequest}
								<p class="mt-0.5 text-sm text-pretty text-muted-foreground">
									Asked for: “{request.buyerRequest}”
								</p>
							{/if}
							<div class="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
								<span
									class={[
										'inline-flex items-center gap-1 rounded-md bg-muted px-1.5 py-0.5',
										e.actor.kind === 'agent' && 'code text-primary'
									]}
								>
									<span class="sr-only">{a.label}</span>{e.actor.name}
								</span>
								{#if showOrganisation && e.organisationName}
									<span class="rounded-md bg-muted px-1.5 py-0.5">{e.organisationName}</span>
								{/if}
								{#if e.outcome}<OutcomeBadge outcome={e.outcome} />{/if}
								{#each e.reasonCodes ?? [] as code (code)}
									<span class="rounded-md bg-muted px-1.5 py-0.5 code">{code}</span>
								{/each}
								<span class="code text-muted-foreground">{e.type}</span>
								{#if request?.previousQuoteId}
									<span class="code text-muted-foreground"
										>revises quote {shortId(request.previousQuoteId)}</span
									>
								{/if}
								{#if order}
									{#if linkOrders}
										<a
											href={resolve(`inbox/${order}`)}
											class="code text-primary underline-offset-2 hover:underline"
											>order {shortId(order)}</a
										>
									{:else}
										<span class="code text-muted-foreground">order {shortId(order)}</span>
									{/if}
								{/if}
							</div>
							<Collapsible.Root class="mt-1.5 text-xs text-muted-foreground">
								<Collapsible.Trigger
									class="group/trigger inline-flex items-center gap-0.5 hover:text-foreground"
								>
									<ChevronRightIcon
										class="size-3 transition-transform group-data-[state=open]/trigger:rotate-90"
									/>
									Recorded data
								</Collapsible.Trigger>
								<Collapsible.Content>
									<dl
										class="mt-1.5 grid grid-cols-[5.5rem_1fr] gap-x-2 gap-y-0.5 rounded-md bg-muted/60 p-2 code break-all"
									>
										<dt>entry</dt>
										<dd class="text-foreground/80">{e.id}</dd>
										{#if e.subjectId}<dt>about</dt>
											<dd class="text-foreground/80">{e.subjectId}</dd>{/if}
										<dt>recorded</dt>
										<dd class="text-foreground/80">{e.at}</dd>
									</dl>
									{#if Object.keys(e.payload).length}
										<pre
											class="mt-1 max-h-80 overflow-auto rounded-md bg-muted/60 p-2 code text-foreground/80">{JSON.stringify(
												e.payload,
												null,
												2
											)}</pre>
									{/if}
								</Collapsible.Content>
							</Collapsible.Root>
						</div>
					</li>
				{/each}
			</ol>
		</section>
	{/each}
</div>
