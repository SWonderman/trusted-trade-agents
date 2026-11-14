<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import ArrowLeftRightIcon from '@lucide/svelte/icons/arrow-left-right';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import XIcon from '@lucide/svelte/icons/x';
	import OrderLineDetail from '#lib/components/domain/OrderLineDetail.svelte';
	import ReasonList from '#lib/components/domain/ReasonList.svelte';
	import OutcomeBadge from '#lib/components/app/OutcomeBadge.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Collapsible from '#lib/components/ui/collapsible/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import * as Sheet from '#lib/components/ui/sheet/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import {
		date,
		dateTime,
		money,
		moneyWhole,
		number,
		relative,
		statusLabel,
		statusTone
	} from '#lib/format.js';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	let order = $derived(data.order);
	let pending = $derived(order.status === 'PENDING_APPROVAL');
	let busy = $state<'approve' | 'reject' | null>(null);
	let note = $state('');
</script>

<svelte:head><title>{order.orderId} · Approvals · Saint Elmo</title></svelte:head>

<Sheet.Root
	open
	onOpenChange={(open) => {
		if (!open) goto(resolve('inbox'), { reset: false });
	}}
>
	<Sheet.Content side="right" class="gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-2xl">
		<!-- Who, what, how much: everything needed to place the order in one glance -->
		<Sheet.Header class="border-b px-6 pt-6 pb-5">
			<div class="flex items-start justify-between gap-6 pr-8">
				<div class="min-w-0">
					<div class="flex flex-wrap items-center gap-2.5">
						<Sheet.Title class="code text-lg">{order.orderId}</Sheet.Title>
						<OutcomeBadge outcome={statusTone[order.status]} label={statusLabel[order.status]} />
					</div>
					<Sheet.Description class="mt-1.5">
						<span class="code">{order.agent.name}</span> · {relative(order.createdAt)} · deliver by
						{date(order.deliverBy)}
					</Sheet.Description>
				</div>
				<div class="shrink-0 text-right">
					<p class="text-2xl font-semibold tracking-tight tabular">{money(order.totals.net)}</p>
					<p class="text-xs text-muted-foreground tabular">excl. VAT</p>
				</div>
			</div>
		</Sheet.Header>

		<div class="flex-1 space-y-7 overflow-y-auto px-6 py-6">
			<!-- The request and the agent's reasoning, in words -->
			<section class="space-y-4">
				{#if order.buyerRequest}
					<div>
						<p class="text-xs text-muted-foreground">Asked for</p>
						<p class="mt-1 font-display text-xl leading-snug">“{order.buyerRequest}”</p>
					</div>
				{/if}
				{#if order.rationale}
					<div class="border-l-2 border-gold/60 pl-4">
						<p class="text-xs text-muted-foreground">
							The agent’s rationale · shown to you, never used by the policy
						</p>
						<p class="mt-1 font-display text-base leading-relaxed text-pretty italic">
							{order.rationale}
						</p>
					</div>
				{/if}
			</section>

			<section aria-labelledby="why-heading">
				<div class="mb-3 flex items-baseline justify-between gap-2">
					<h3 id="why-heading" class="text-sm font-semibold">Why it’s here</h3>
					<p class="text-xs text-muted-foreground">mandate v{order.policy.mandateVersion}</p>
				</div>
				<ReasonList reasons={order.policy.reasons} />
			</section>

			{#if order.changes.length}
				<section class="rounded-lg bg-hold/8 px-4 py-3 text-sm">
					<p class="flex items-center gap-2 font-medium text-hold">
						<RefreshCwIcon class="size-4" aria-hidden="true" /> Changed since the quote
					</p>
					<ul class="mt-1 space-y-0.5">
						{#each order.changes as ch (ch.lineRef + ch.field)}
							<li class="tabular">
								Line {ch.lineRef.slice(1)}: {ch.field === 'unitPrice' ? 'price per unit' : ch.field}
								{typeof ch.quoted === 'number' ? money(ch.quoted) : ch.quoted} →
								<span class="font-semibold"
									>{typeof ch.now === 'number' ? money(ch.now) : ch.now}</span
								>
							</li>
						{/each}
					</ul>
				</section>
			{/if}

			<!-- Lines: one row each; the full conversion, offer and provenance open on demand -->
			<section aria-labelledby="lines-heading">
				<h3 id="lines-heading" class="mb-3 text-sm font-semibold">
					What would be ordered
					<span class="font-normal text-muted-foreground">· {order.lines.length}</span>
				</h3>
				<ul class="divide-y rounded-xl border bg-card">
					{#each order.lines as line (line.ref)}
						<li>
							<Collapsible.Root>
								<Collapsible.Trigger
									class="group/line flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted/50"
								>
									<div class="min-w-0 flex-1">
										<p class="truncate text-sm font-medium">{line.product.name}</p>
										<p
											class="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground tabular"
										>
											{number(line.quantity)}
											{line.product.salesUnit} × {money(line.offer.unitPrice)}
											{#if line.substitutesFor}
												<span class="inline-flex items-center gap-1 text-hold">
													· <ArrowLeftRightIcon class="size-3" aria-hidden="true" /> substitute
												</span>
											{/if}
										</p>
									</div>
									<span class="text-sm font-medium tabular">{money(line.lineTotal)}</span>
									<ChevronDownIcon
										class="size-4 text-muted-foreground transition-transform group-data-[state=open]/line:rotate-180"
										aria-hidden="true"
									/>
								</Collapsible.Trigger>
								<Collapsible.Content class="px-3 pb-3">
									<OrderLineDetail {line} deliverBy={order.deliverBy} />
								</Collapsible.Content>
							</Collapsible.Root>
						</li>
					{/each}
				</ul>
			</section>

			{#if data.mandate && data.periodSpend}
				<p class="text-xs leading-relaxed text-muted-foreground">
					The mandate lets <span class="code">{order.agent.name}</span> decide alone up to
					{moneyWhole(data.mandate.autoApproveUpTo)}, never above
					{moneyWhole(data.mandate.maxOrderTotal)}; {moneyWhole(data.periodSpend.committed)} of
					{moneyWhole(data.mandate.periodSpendCap)} is spent this
					{data.mandate.spendPeriod === 'WEEK' ? 'week' : 'month'}.
					<a
						href={resolve(`agents/${order.agent.id}`)}
						class="font-medium text-foreground underline underline-offset-2">See the mandate</a
					>
				</p>
			{/if}

			{#if !pending}
				<section aria-labelledby="history-heading">
					<h3 id="history-heading" class="mb-2 text-sm font-semibold">History</h3>
					<ol class="space-y-1.5 text-sm">
						{#each order.statusHistory as h (h.at + h.status)}
							<li class="flex flex-wrap items-center gap-x-3 gap-y-1">
								<span class="w-28 text-xs text-muted-foreground tabular">{dateTime(h.at)}</span>
								<span class="font-medium">{statusLabel[h.status]}</span>
								<span class="text-muted-foreground">by {h.by.replace(/^(agent|user):/, '')}</span>
								{#if h.note}<span class="italic">“{h.note}”</span>{/if}
							</li>
						{/each}
					</ol>
					<a
						href="{resolve('audit')}?order={order.orderId}"
						class="mt-3 inline-block text-xs font-medium underline underline-offset-2"
						>Full audit trail for this order</a
					>
				</section>
			{/if}
		</div>

		{#if pending}
			<Sheet.Footer class="border-t px-6 py-4">
				<form
					method="POST"
					class="w-full space-y-3"
					use:enhance={({ action }) => {
						busy = action.search.includes('reject') ? 'reject' : 'approve';
						return async ({ update, result }) => {
							await update({ reset: false });
							// The drawer is reused for the next order in the queue, so start with an empty note.
							if (result.type === 'redirect') note = '';
							busy = null;
						};
					}}
				>
					<div class="space-y-1.5">
						<Label for="note">
							Note for the agent and the audit trail
							<span class="font-normal text-muted-foreground">(needed to reject)</span>
						</Label>
						<Input
							id="note"
							name="note"
							placeholder="e.g. Fine for this week, we have a buffet on Monday"
							bind:value={note}
							maxlength={500}
						/>
					</div>
					{#if form?.error}
						<p role="alert" class="text-sm text-stop">{form.error}</p>
					{/if}
					<div class="flex flex-wrap items-center justify-between gap-3">
						<p class="text-xs text-muted-foreground">
							Approving re-checks live price, stock and closing time first.
						</p>
						<div class="flex shrink-0 gap-2">
							<Button
								type="submit"
								variant="destructive"
								formaction="?/reject"
								disabled={busy !== null}
							>
								{#if busy === 'reject'}<Spinner />Rejecting…{:else}<XIcon />Reject{/if}
							</Button>
							<Button type="submit" formaction="?/approve" disabled={busy !== null}>
								{#if busy === 'approve'}<Spinner />Placing…{:else}<CheckIcon />Approve and place{/if}
							</Button>
						</div>
					</div>
				</form>
			</Sheet.Footer>
		{/if}
	</Sheet.Content>
</Sheet.Root>
