<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import ArrowLeftRightIcon from '@lucide/svelte/icons/arrow-left-right';
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronDownIcon from '@lucide/svelte/icons/chevron-down';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import XIcon from '@lucide/svelte/icons/x';
	import OrderLineDetail from '#lib/components/domain/OrderLineDetail.svelte';
	import ReasonList from '#lib/components/domain/ReasonList.svelte';
	import OutcomeBadge from '#lib/components/app/OutcomeBadge.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Collapsible from '#lib/components/ui/collapsible/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Progress } from '#lib/components/ui/progress/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import type { OrderLine } from '#lib/api/types.js';
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

	/** One short verdict on whether a line can arrive as asked. */
	function availability(line: OrderLine) {
		const o = line.offer;
		const daysLate = Math.round(
			(new Date(o.availableDate).getTime() - new Date(order.deliverBy).getTime()) / 86_400_000
		);
		if (o.availableAmount !== null && o.availableAmount < line.quantity)
			return { text: `only ${number(o.availableAmount)} in stock`, tone: 'text-stop' };
		if (daysLate > 0)
			return { text: `${daysLate} day${daysLate > 1 ? 's' : ''} late`, tone: 'text-hold' };
		if (o.availableAmount === null)
			return { text: 'supplier stock', tone: 'text-muted-foreground' };
		return { text: 'in stock, on time', tone: 'text-ok' };
	}

	let used = $derived(
		data.mandate && data.periodSpend
			? Math.min(100, (data.periodSpend.committed / data.mandate.periodSpendCap) * 100)
			: 0
	);
</script>

<svelte:head><title>{order.orderId} · Approvals · Saint Elmo</title></svelte:head>

<Dialog.Root
	open
	onOpenChange={(open) => {
		if (!open) goto(resolve('inbox'), { reset: false });
	}}
>
	<Dialog.Content class="flex h-[min(92dvh,56rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-6xl">
		<!-- Header: what was asked, by whom, for how much -->
		<header class="border-b px-6 pt-6 pb-5 sm:px-8">
			<div class="flex flex-wrap items-center gap-x-3 gap-y-1 pr-10 text-sm text-muted-foreground">
				<span class="code font-medium text-foreground">{order.orderId}</span>
				<OutcomeBadge outcome={statusTone[order.status]} label={statusLabel[order.status]} />
				<span><span class="code">{order.agent.name}</span> · {relative(order.createdAt)}</span>
				<span>deliver by {date(order.deliverBy)}</span>
			</div>
			<div class="mt-3 flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
				<Dialog.Title
					class="max-w-[40ch] font-display-tight text-[1.75rem] text-balance sm:text-[2rem]"
				>
					{order.buyerRequest ? `“${order.buyerRequest}”` : `Order ${order.orderId}`}
				</Dialog.Title>
				<div class="text-right">
					<p class="text-3xl font-semibold tracking-tight tabular">{money(order.totals.net)}</p>
					<p class="text-xs text-muted-foreground tabular">
						excl. VAT · {money(order.totals.gross)} with VAT
					</p>
				</div>
			</div>
			<Dialog.Description class="sr-only">
				Review why the policy sent this order to a person, then approve or reject it.
			</Dialog.Description>
		</header>

		<div
			class="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)] overflow-y-auto lg:grid-cols-[minmax(0,1fr)_22rem]"
		>
			<!-- Main: the policy's reasons, then the lines -->
			<div class="space-y-8 px-6 py-6 sm:px-8">
				<section aria-labelledby="why-heading">
					<h3 id="why-heading" class="mb-3 text-sm font-semibold">Why it’s here</h3>
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
									Line {ch.lineRef.slice(1)}: {ch.field === 'unitPrice'
										? 'price per unit'
										: ch.field}
									{typeof ch.quoted === 'number' ? money(ch.quoted) : ch.quoted} →
									<span class="font-semibold"
										>{typeof ch.now === 'number' ? money(ch.now) : ch.now}</span
									>
								</li>
							{/each}
						</ul>
					</section>
				{/if}

				<section aria-labelledby="lines-heading">
					<h3 id="lines-heading" class="mb-3 text-sm font-semibold">
						What would be ordered
						<span class="font-normal text-muted-foreground">· {order.lines.length}</span>
					</h3>
					<div class="overflow-hidden rounded-xl border">
						<div
							class="hidden grid-cols-[minmax(0,1fr)_10rem_8rem_6.5rem_1rem] gap-3 border-b bg-muted/50 px-4 py-2 text-xs font-medium text-muted-foreground md:grid"
							aria-hidden="true"
						>
							<span>Product</span>
							<span>Quantity</span>
							<span>Availability</span>
							<span class="text-right">Total</span>
							<span></span>
						</div>
						<ul class="divide-y">
							{#each order.lines as line (line.ref)}
								{@const a = availability(line)}
								<li>
									<Collapsible.Root>
										<Collapsible.Trigger
											class="group/line grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-4 py-3 text-left text-sm hover:bg-muted/40 md:grid-cols-[minmax(0,1fr)_10rem_8rem_6.5rem_1rem]"
										>
											<span class="min-w-0">
												<span class="line-clamp-2 font-medium text-pretty">{line.product.name}</span
												>
												<span class="flex items-center gap-1.5 text-xs text-muted-foreground">
													<span class="code">{line.product.code}</span>
													{#if line.substitutesFor}
														<span class="inline-flex items-center gap-1 text-hold">
															<ArrowLeftRightIcon class="size-3" aria-hidden="true" />substitute
														</span>
													{/if}
												</span>
											</span>
											<span class="tabular">
												<span class="block">
													{number(line.quantity)}
													{line.product.salesUnit}
													<span class="text-muted-foreground">× {money(line.offer.unitPrice)}</span>
												</span>
												{#if line.conversion}
													<span class="block text-xs text-muted-foreground">
														from {number(line.conversion.requested.amount)}
														{line.conversion.requested.unit}
													</span>
												{/if}
											</span>
											<span class={['text-xs', a.tone]}>{a.text}</span>
											<span class="text-right font-medium tabular">{money(line.lineTotal)}</span>
											<ChevronDownIcon
												class="hidden size-4 text-muted-foreground transition-transform group-data-[state=open]/line:rotate-180 md:block"
												aria-hidden="true"
											/>
										</Collapsible.Trigger>
										<Collapsible.Content class="bg-muted/30 px-3 pb-3">
											<OrderLineDetail {line} deliverBy={order.deliverBy} />
										</Collapsible.Content>
									</Collapsible.Root>
								</li>
							{/each}
						</ul>
					</div>
				</section>
			</div>

			<!-- Side: the agent's words and the mandate it acts under -->
			<aside class="space-y-7 border-t bg-muted/35 px-6 py-6 sm:px-8 lg:border-t-0 lg:border-l">
				<section>
					<h3 class="text-sm font-semibold">The agent’s rationale</h3>
					<p class="mt-0.5 text-xs text-muted-foreground">
						Shown to you, never used by the policy.
					</p>
					{#if order.rationale}
						<p class="mt-3 border-l-2 border-gold/60 pl-3 text-sm leading-relaxed text-pretty">
							{order.rationale}
						</p>
					{:else}
						<p class="mt-3 text-sm text-muted-foreground">The agent didn’t explain this order.</p>
					{/if}
				</section>

				{#if data.mandate && data.periodSpend}
					<section class="space-y-3 border-t pt-6">
						<div class="flex items-baseline justify-between gap-2">
							<h3 class="text-sm font-semibold">Its mandate</h3>
							<a
								href={resolve(`agents/${order.agent.id}`)}
								class="text-xs font-medium underline underline-offset-2">Open</a
							>
						</div>
						<dl class="space-y-2 text-sm">
							<div class="flex justify-between gap-3">
								<dt class="text-muted-foreground">Decides alone up to</dt>
								<dd class="font-medium tabular">{moneyWhole(data.mandate.autoApproveUpTo)}</dd>
							</div>
							<div class="flex justify-between gap-3">
								<dt class="text-muted-foreground">Never above</dt>
								<dd class="font-medium tabular">{moneyWhole(data.mandate.maxOrderTotal)}</dd>
							</div>
							<div>
								<div class="flex justify-between gap-3">
									<dt class="text-muted-foreground">
										Spent this {data.mandate.spendPeriod === 'WEEK' ? 'week' : 'month'}
									</dt>
									<dd class="font-medium tabular">
										{moneyWhole(data.periodSpend.committed)}
										<span class="font-normal text-muted-foreground"
											>/ {moneyWhole(data.mandate.periodSpendCap)}</span
										>
									</dd>
								</div>
								<Progress
									value={used}
									class="mt-2 h-1.5"
									aria-label="Share of the spend cap used"
								/>
							</div>
						</dl>
					</section>
				{/if}

				{#if !pending}
					<section class="border-t pt-6">
						<h3 class="mb-2 text-sm font-semibold">History</h3>
						<ol class="space-y-2 text-sm">
							{#each order.statusHistory as h (h.at + h.status)}
								<li>
									<p>
										<span class="font-medium">{statusLabel[h.status]}</span>
										<span class="text-muted-foreground"
											>by {h.by.replace(/^(agent|user):/, '')}</span
										>
									</p>
									<p class="text-xs text-muted-foreground tabular">{dateTime(h.at)}</p>
									{#if h.note}<p class="mt-0.5 italic">“{h.note}”</p>{/if}
								</li>
							{/each}
						</ol>
						<a
							href="{resolve('audit')}?order={order.orderId}"
							class="mt-3 inline-block text-xs font-medium underline underline-offset-2"
							>Full audit trail</a
						>
					</section>
				{/if}
			</aside>
		</div>

		{#if pending}
			<!-- Decision: one row, always in view -->
			<footer class="border-t bg-card px-6 py-4 sm:px-8">
				<form
					method="POST"
					class="flex flex-col gap-3 md:flex-row md:items-center"
					use:enhance={({ action }) => {
						busy = action.search.includes('reject') ? 'reject' : 'approve';
						return async ({ update, result }) => {
							await update({ reset: false });
							// The modal is reused for the next order in the queue, so start with an empty note.
							if (result.type === 'redirect') note = '';
							busy = null;
						};
					}}
				>
					<label for="note" class="sr-only">Note for the agent and the audit trail</label>
					<Input
						id="note"
						name="note"
						class="md:flex-1"
						placeholder="Note for the agent and the audit trail (needed to reject)"
						bind:value={note}
						maxlength={500}
					/>
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
				</form>
				{#if form?.error}
					<p role="alert" class="mt-2 text-sm text-stop">{form.error}</p>
				{:else}
					<p class="mt-2 text-xs text-muted-foreground">
						Approving re-checks live price, stock and closing time first; if a hard rule fails now,
						the order is rejected instead.
					</p>
				{/if}
			</footer>
		{/if}
	</Dialog.Content>
</Dialog.Root>
