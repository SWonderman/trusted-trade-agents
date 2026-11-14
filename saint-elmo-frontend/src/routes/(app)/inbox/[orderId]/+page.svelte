<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import OrderLineDetail from '#lib/components/domain/OrderLineDetail.svelte';
	import ReasonList from '#lib/components/domain/ReasonList.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import OutcomeBadge from '#lib/components/ui/OutcomeBadge.svelte';
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

<svelte:head><title>{order.orderId} · Approval inbox · Saint Elmo</title></svelte:head>

<article class="panel overflow-hidden" aria-labelledby="order-title">
	<header class="border-b border-line px-5 py-5 sm:px-6">
		<a
			href={resolve('inbox')}
			class="mb-3 inline-flex items-center gap-1 text-sm text-muted lg:hidden"
		>
			<span class="rotate-180"><Icon name="chevronRight" size={14} /></span> Back to the inbox
		</a>
		<div class="flex flex-wrap items-start justify-between gap-4">
			<div class="min-w-0">
				<div class="flex flex-wrap items-center gap-3">
					<h2 id="order-title" class="code text-lg font-semibold text-ink">{order.orderId}</h2>
					<OutcomeBadge outcome={statusTone[order.status]} label={statusLabel[order.status]} />
				</div>
				<p class="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
					<span>Placed by <span class="font-medium text-ink">{order.agent.name}</span></span>
					<span>{relative(order.createdAt)}</span>
					<span>Deliver by <span class="text-ink">{date(order.deliverBy)}</span></span>
					<span>From quote <span class="code">{order.quoteId}</span></span>
				</p>
			</div>
			<div class="text-right">
				<p class="tabular text-2xl font-semibold tracking-tight text-ink">
					{money(order.totals.net)}
				</p>
				<p class="tabular text-xs text-muted">
					excl. VAT; {money(order.totals.gross)} with VAT{#if order.totals.deposits}, plus {money(
							order.totals.deposits
						)} deposits{/if}
				</p>
			</div>
		</div>

		{#if order.buyerRequest}
			<figure class="mt-4 border-l-2 border-line-strong pl-3">
				<figcaption class="text-xs text-muted">What the buyer asked for</figcaption>
				<blockquote class="mt-0.5 text-[0.9375rem] text-ink">“{order.buyerRequest}”</blockquote>
			</figure>
		{/if}
	</header>

	<!-- Ledger and margin: the deterministic verdict reads as the text; the agent's note sits in the margin. -->
	<div class="grid xl:grid-cols-[1fr_18rem]">
		<div class="min-w-0 px-5 py-5 sm:px-6">
			<section aria-labelledby="policy-heading">
				<div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
					<h3 id="policy-heading" class="font-semibold text-ink">Why it’s here</h3>
					<p class="text-xs text-muted">
						Checked by the policy against mandate v{order.policy.mandateVersion}
					</p>
				</div>
				<ReasonList reasons={order.policy.reasons} />
			</section>

			{#if order.changes.length}
				<section
					class="mt-6 rounded-sm border border-hold/30 bg-hold-wash px-4 py-3"
					aria-labelledby="changes-heading"
				>
					<h3 id="changes-heading" class="text-sm font-semibold text-hold">
						Changed since the quote
					</h3>
					<ul class="mt-1 space-y-0.5 text-sm text-ink">
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
					<p class="mt-1 text-xs text-muted">The policy ran again with the new values.</p>
				</section>
			{/if}

			<section class="mt-8" aria-labelledby="lines-heading">
				<h3 id="lines-heading" class="mb-3 font-semibold text-ink">
					What would be ordered
					<span class="font-normal text-muted"
						>({order.lines.length} {order.lines.length === 1 ? 'line' : 'lines'})</span
					>
				</h3>
				<div class="divide-y divide-line">
					{#each order.lines as line (line.ref)}
						<OrderLineDetail {line} deliverBy={order.deliverBy} />
					{/each}
				</div>
			</section>
		</div>

		<aside
			class="border-t border-line bg-margin px-5 py-5 sm:px-6 xl:border-t-0 xl:border-l"
			aria-labelledby="margin-heading"
		>
			<h3 id="margin-heading" class="text-sm font-semibold text-ink">Agent’s note</h3>
			<p class="mt-0.5 text-xs text-muted">
				Written by {order.agent.name}. Not used in the decision.
			</p>
			{#if order.rationale}
				<p class="rationale mt-3 text-ink">{order.rationale}</p>
			{:else}
				<p class="mt-3 text-sm text-muted">The agent didn’t explain this order.</p>
			{/if}

			{#if data.mandate && data.periodSpend}
				<dl class="mt-6 space-y-2 border-t border-line pt-4 text-sm">
					<div class="flex justify-between gap-3">
						<dt class="text-muted">Auto-approve up to</dt>
						<dd class="tabular text-ink">{moneyWhole(data.mandate.autoApproveUpTo)}</dd>
					</div>
					<div class="flex justify-between gap-3">
						<dt class="text-muted">Order limit</dt>
						<dd class="tabular text-ink">{moneyWhole(data.mandate.maxOrderTotal)}</dd>
					</div>
					<div class="flex justify-between gap-3">
						<dt class="text-muted">
							Spent this {data.mandate.spendPeriod === 'WEEK' ? 'week' : 'month'}
						</dt>
						<dd class="tabular text-ink">
							{moneyWhole(data.periodSpend.committed)} of {moneyWhole(data.mandate.periodSpendCap)}
						</dd>
					</div>
				</dl>
				<a
					href={resolve(`agents/${order.agent.id}`)}
					class="mt-3 inline-block text-sm text-lapis underline-offset-2 hover:underline"
				>
					See the full mandate
				</a>
			{/if}
		</aside>
	</div>

	{#if pending}
		<footer
			class="sticky bottom-0 border-t border-line bg-panel/95 px-5 py-4 backdrop-blur sm:px-6"
		>
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
				<div class="flex-1">
					<label for="note" class="field-label">
						Note for the agent and the audit trail
						<span class="font-normal text-muted">(needed to reject)</span>
					</label>
					<input
						id="note"
						name="note"
						class="input"
						placeholder="e.g. Fine for this week, we have a buffet on Monday"
						bind:value={note}
						maxlength="500"
					/>
				</div>
				<div class="flex gap-2">
					<button class="btn btn-danger" formaction="?/reject" disabled={busy !== null}>
						<Icon name="x" />
						{busy === 'reject' ? 'Rejecting…' : 'Reject'}
					</button>
					<button class="btn btn-primary" formaction="?/approve" disabled={busy !== null}>
						<Icon name="check" />
						{busy === 'approve' ? 'Re-checking and placing…' : 'Approve and place order'}
					</button>
				</div>
			</form>
			{#if form?.error}
				<p role="alert" class="mt-2 text-sm text-stop">{form.error}</p>
			{/if}
			<p class="mt-2 text-xs text-muted">
				Approving re-checks live price, stock and closing time first. If a hard rule fails now, the
				order is rejected instead.
			</p>
		</footer>
	{:else}
		<footer class="border-t border-line px-5 py-4 sm:px-6">
			<h3 class="text-sm font-semibold text-ink">History</h3>
			<ol class="mt-2 space-y-1.5 text-sm">
				{#each order.statusHistory as h, i (i)}
					<li class="flex flex-wrap gap-x-3">
						<span class="tabular text-muted">{dateTime(h.at)}</span>
						<span class="font-medium text-ink">{statusLabel[h.status]}</span>
						<span class="text-muted">by {h.by.replace(/^(agent|user):/, '')}</span>
						{#if h.note}<span class="text-ink">“{h.note}”</span>{/if}
					</li>
				{/each}
			</ol>
			<a
				href="{resolve('audit')}?order={order.orderId}"
				class="mt-3 inline-block text-sm text-lapis hover:underline"
			>
				Full audit trail for this order
			</a>
		</footer>
	{/if}
</article>

<style>
	.rationale {
		font-family: var(--font-serif);
		font-style: italic;
		font-size: 1.0625rem;
		line-height: 1.55;
		hanging-punctuation: first;
	}
</style>
