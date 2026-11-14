<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import ArrowLeftIcon from '@lucide/svelte/icons/arrow-left';
	import CheckIcon from '@lucide/svelte/icons/check';
	import QuoteIcon from '@lucide/svelte/icons/quote';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import XIcon from '@lucide/svelte/icons/x';
	import OrderLineDetail from '#lib/components/domain/OrderLineDetail.svelte';
	import ReasonList from '#lib/components/domain/ReasonList.svelte';
	import OutcomeBadge from '#lib/components/app/OutcomeBadge.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { Progress } from '#lib/components/ui/progress/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import {
		date,
		dateTime,
		money,
		moneyWhole,
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

<article class="overflow-hidden rounded-2xl border bg-card shadow-xs" aria-labelledby="order-title">
	<header class="border-b px-5 py-5 sm:px-7 sm:py-6">
		<Button href={resolve('inbox')} variant="ghost" size="sm" class="mb-3 -ml-2 lg:hidden">
			<ArrowLeftIcon /> Back to approvals
		</Button>
		<div class="flex flex-wrap items-start justify-between gap-x-6 gap-y-4">
			<div class="min-w-0">
				<div class="flex flex-wrap items-center gap-3">
					<h2 id="order-title" class="code text-xl font-semibold">{order.orderId}</h2>
					<OutcomeBadge outcome={statusTone[order.status]} label={statusLabel[order.status]} />
				</div>
				<p class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
					<span>by <span class="code text-primary">{order.agent.name}</span></span>
					<span>{relative(order.createdAt)}</span>
					<span>deliver by <span class="text-foreground">{date(order.deliverBy)}</span></span>
					<span>quote <span class="code">{order.quoteId}</span></span>
				</p>
			</div>
			<div class="sm:text-right">
				<p class="text-3xl font-semibold tracking-tight tabular">{money(order.totals.net)}</p>
				<p class="mt-0.5 text-xs text-muted-foreground tabular">
					excl. VAT · {money(order.totals.gross)} with VAT{#if order.totals.deposits}
						· +{money(order.totals.deposits)} deposits{/if}
				</p>
			</div>
		</div>

		{#if order.buyerRequest}
			<figure class="relative mt-5 flex flex-col rounded-xl bg-muted/60 py-3 pr-4 pl-11">
				<blockquote class="mt-0.5 font-display text-lg leading-snug">
					<QuoteIcon
						class="absolute top-3.5 left-4 size-4 text-gold-deep dark:text-gold"
						aria-hidden="true"
					/>
					{order.buyerRequest}
				</blockquote>
				<figcaption class="order-first text-xs text-muted-foreground">
					What the buyer asked for
				</figcaption>
			</figure>
		{/if}
	</header>

	<!-- Ledger and margin: the deterministic verdict is the text; the agent's note sits in the margin. -->
	<div class="grid 2xl:grid-cols-[1fr_19rem]">
		<div class="min-w-0 space-y-8 px-5 py-6 sm:px-7">
			<section aria-labelledby="policy-heading">
				<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
					<h3 id="policy-heading" class="font-semibold">Why it’s here</h3>
					<p class="text-xs text-muted-foreground">
						Policy checked against mandate v{order.policy.mandateVersion}
					</p>
				</div>
				<ReasonList reasons={order.policy.reasons} />
			</section>

			{#if order.changes.length}
				<section
					class="rounded-xl border border-hold/30 bg-hold/6 px-4 py-3"
					aria-labelledby="changes-heading"
				>
					<h3 id="changes-heading" class="flex items-center gap-2 text-sm font-semibold text-hold">
						<RefreshCwIcon class="size-4" aria-hidden="true" /> Changed since the quote
					</h3>
					<ul class="mt-1.5 space-y-0.5 text-sm">
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
					<p class="mt-1 text-xs text-muted-foreground">
						The policy ran again with the new values.
					</p>
				</section>
			{/if}

			<section aria-labelledby="lines-heading">
				<h3 id="lines-heading" class="mb-3 font-semibold">
					What would be ordered
					<span class="font-normal text-muted-foreground"
						>· {order.lines.length} {order.lines.length === 1 ? 'line' : 'lines'}</span
					>
				</h3>
				<div class="space-y-3">
					{#each order.lines as line (line.ref)}
						<OrderLineDetail {line} deliverBy={order.deliverBy} />
					{/each}
				</div>
			</section>
		</div>

		<aside
			class="border-b bg-muted/35 px-5 py-6 max-2xl:order-first sm:px-7 2xl:border-b-0 2xl:border-l"
			aria-labelledby="margin-heading"
		>
			<h3 id="margin-heading" class="text-sm font-semibold">Agent’s rationale</h3>
			<p class="mt-0.5 text-xs text-muted-foreground">
				Written by {order.agent.name}. Shown to you, never used by the policy.
			</p>
			{#if order.rationale}
				<p class="mt-4 font-display text-[1.1875rem] leading-relaxed text-pretty italic">
					{order.rationale}
				</p>
			{:else}
				<p class="mt-4 text-sm text-muted-foreground">The agent didn’t explain this order.</p>
			{/if}

			{#if data.mandate && data.periodSpend}
				{@const used = Math.min(
					100,
					(data.periodSpend.committed / data.mandate.periodSpendCap) * 100
				)}
				<dl class="mt-7 space-y-2.5 border-t pt-5 text-sm">
					<div class="flex justify-between gap-3">
						<dt class="text-muted-foreground">Decides alone up to</dt>
						<dd class="tabular">{moneyWhole(data.mandate.autoApproveUpTo)}</dd>
					</div>
					<div class="flex justify-between gap-3">
						<dt class="text-muted-foreground">Order limit</dt>
						<dd class="tabular">{moneyWhole(data.mandate.maxOrderTotal)}</dd>
					</div>
					<div>
						<div class="flex justify-between gap-3">
							<dt class="text-muted-foreground">
								Spent this {data.mandate.spendPeriod === 'WEEK' ? 'week' : 'month'}
							</dt>
							<dd class="tabular">
								{moneyWhole(data.periodSpend.committed)} / {moneyWhole(data.mandate.periodSpendCap)}
							</dd>
						</div>
						<Progress value={used} class="mt-2 h-1.5" aria-label="Share of the spend cap used" />
					</div>
				</dl>
				<Button
					href={resolve(`agents/${order.agent.id}`)}
					variant="link"
					size="sm"
					class="mt-3 px-0"
				>
					See the full mandate
				</Button>
			{/if}
		</aside>
	</div>

	{#if pending}
		<footer class="sticky bottom-0 border-t bg-card/95 px-5 py-4 backdrop-blur sm:px-7">
			<form
				method="POST"
				class="flex flex-col gap-3 md:flex-row md:items-end"
				use:enhance={({ action }) => {
					busy = action.search.includes('reject') ? 'reject' : 'approve';
					return async ({ update, result }) => {
						await update({ reset: false });
						// The page is reused for the next order in the queue, so start it with an empty note.
						if (result.type === 'redirect') note = '';
						busy = null;
					};
				}}
			>
				<div class="flex-1 space-y-1.5">
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
						aria-invalid={form?.error && form.action === 'reject' ? 'true' : undefined}
					/>
				</div>
				<div class="flex gap-2">
					<Button
						type="submit"
						variant="destructive"
						formaction="?/reject"
						disabled={busy !== null}
					>
						{#if busy === 'reject'}<Spinner />Rejecting…{:else}<XIcon />Reject{/if}
					</Button>
					<Button type="submit" formaction="?/approve" disabled={busy !== null}>
						{#if busy === 'approve'}<Spinner />Re-checking and placing…{:else}<CheckIcon />Approve
							and place{/if}
					</Button>
				</div>
			</form>
			{#if form?.error}
				<p role="alert" class="mt-2 text-sm text-stop">{form.error}</p>
			{/if}
			<p class="mt-2 text-xs text-muted-foreground">
				Approving re-checks live price, stock and closing time first. If a hard rule fails now, the
				order is rejected instead.
			</p>
		</footer>
	{:else}
		<footer class="border-t px-5 py-5 sm:px-7">
			<h3 class="text-sm font-semibold">History</h3>
			<ol class="mt-3 space-y-2 text-sm">
				{#each order.statusHistory as h (h.at + h.status)}
					<li class="flex flex-wrap items-center gap-x-3 gap-y-1">
						<span class="w-28 text-muted-foreground tabular">{dateTime(h.at)}</span>
						<OutcomeBadge outcome={statusTone[h.status]} label={statusLabel[h.status]} />
						<span class="text-muted-foreground">by {h.by.replace(/^(agent|user):/, '')}</span>
						{#if h.note}<span class="italic">“{h.note}”</span>{/if}
					</li>
				{/each}
			</ol>
			<Button
				href="{resolve('audit')}?order={order.orderId}"
				variant="link"
				size="sm"
				class="mt-2 px-0"
			>
				Full audit trail for this order
			</Button>
		</footer>
	{/if}
</article>
