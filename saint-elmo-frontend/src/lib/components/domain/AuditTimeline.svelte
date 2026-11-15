<script lang="ts">
	import { resolve } from '$app/paths';
	import BotIcon from '@lucide/svelte/icons/bot';
	import CogIcon from '@lucide/svelte/icons/cog';
	import UserIcon from '@lucide/svelte/icons/user';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import type { AuditEvent } from '#lib/api/types.js';
	import { date, time } from '#lib/format.js';
	import * as Collapsible from '#lib/components/ui/collapsible/index.js';
	import OutcomeBadge from '../app/OutcomeBadge.svelte';

	let {
		events,
		showOrganisation = false,
		linkOrders = true,
		contained = false
	}: {
		events: AuditEvent[];
		showOrganisation?: boolean;
		linkOrders?: boolean;
		/** Inside a container that scrolls on large screens: day headings stick to its top there. */
		contained?: boolean;
	} = $props();

	let days = $derived.by(() => {
		const groups: { day: string; events: AuditEvent[] }[] = [];
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
					'sticky top-14 z-[1] -mx-2 mb-3 bg-card/95 px-2 py-1.5 text-xs font-medium tracking-wider text-muted-foreground uppercase backdrop-blur',
					contained && 'lg:top-0'
				]}
			>
				{group.day}
			</h3>
			<ol>
				{#each group.events as e (e.id)}
					{@const a = actor[e.actor.kind]}
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
							<p class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm">
								<span class="sr-only">{a.label}</span>
								<span class={['font-medium', e.actor.kind === 'agent' && 'code text-primary']}>
									{e.actor.name}
								</span>
								<span class="code text-xs text-muted-foreground">{e.tool ?? e.type}</span>
								{#if showOrganisation}<span class="text-xs text-muted-foreground"
										>· {e.organisationName}</span
									>{/if}
							</p>
							<p class="mt-0.5 text-sm text-pretty">{e.summary}</p>
							{#if e.outcome || e.stateChange || e.orderId || e.reasonCodes?.length}
								<div class="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
									{#if e.outcome}<OutcomeBadge outcome={e.outcome} />{/if}
									{#each e.reasonCodes ?? [] as code (code)}
										<span class="rounded-md bg-muted px-1.5 py-0.5 code">{code}</span>
									{/each}
									{#if e.stateChange}
										<span class="code text-muted-foreground">
											{e.stateChange.from ?? 'new'} →
											<span class="text-foreground">{e.stateChange.to}</span>
										</span>
									{/if}
									{#if e.orderId}
										{#if linkOrders}
											<a
												href={resolve(`inbox/${e.orderId}`)}
												class="code text-primary underline-offset-2 hover:underline">{e.orderId}</a
											>
										{:else}
											<span class="code text-muted-foreground">{e.orderId}</span>
										{/if}
									{/if}
								</div>
							{/if}
							<Collapsible.Root class="mt-1.5 text-xs text-muted-foreground">
								<Collapsible.Trigger
									class="group/trigger inline-flex items-center gap-0.5 hover:text-foreground"
								>
									<ChevronRightIcon
										class="size-3 transition-transform group-data-[state=open]/trigger:rotate-90"
									/>
									Entry {e.id}
								</Collapsible.Trigger>
								<Collapsible.Content>
									<dl
										class="mt-1.5 grid grid-cols-[5.5rem_1fr] gap-x-2 gap-y-0.5 rounded-md bg-muted/60 p-2 code break-all"
									>
										<dt>hash</dt>
										<dd class="text-foreground/80">{e.hash}</dd>
										<dt>previous</dt>
										<dd class="text-foreground/80">{e.prevHash}</dd>
										{#if e.quoteId}<dt>quote</dt>
											<dd class="text-foreground/80">{e.quoteId}</dd>{/if}
										<dt>recorded</dt>
										<dd class="text-foreground/80">{e.at}</dd>
									</dl>
								</Collapsible.Content>
							</Collapsible.Root>
						</div>
					</li>
				{/each}
			</ol>
		</section>
	{/each}
</div>
