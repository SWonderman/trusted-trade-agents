<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import AuditTimeline from '#lib/components/domain/AuditTimeline.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const kindLabel = {
		OUT_OF_STOCK: 'Out of stock',
		PARTIAL: 'Partial stock',
		LATE: 'Late delivery',
		PRICE_CHANGE: 'Price change'
	} as const;
</script>

<svelte:head><title>Oversight · Saint Elmo</title></svelte:head>

<div class="mb-6">
	<div class="flex flex-wrap items-center gap-3">
		<h1 class="text-2xl font-semibold tracking-tight text-ink">Oversight</h1>
		<span class="rounded-sm border border-line-strong px-1.5 py-0.5 text-xs text-muted"
			>Read-only</span
		>
	</div>
	<p class="mt-1 max-w-[66ch] text-sm text-muted">
		What every buyer organisation’s agents are doing with Valio Aimo, as it happens. You can read
		this trail but not approve, reject or change anything for a customer.
	</p>
</div>

<dl class="panel mb-6 grid grid-cols-2 divide-line sm:grid-cols-5 sm:divide-x">
	{#each [['Buyer organisations', data.stats.organisations], ['Tool calls, 24 h', data.stats.toolCalls], ['Orders placed, 24 h', data.stats.ordersPlaced], ['Sent to a person, 24 h', data.stats.waiting], ['Rejected by policy, 24 h', data.stats.rejected]] as [label, value] (label)}
		<div class="px-4 py-3">
			<dt class="text-xs text-muted">{label}</dt>
			<dd class="tabular mt-0.5 text-lg font-semibold text-ink">{value}</dd>
		</div>
	{/each}
</dl>

<div class="grid items-start gap-6 xl:grid-cols-[1fr_22rem]">
	<section class="panel min-w-0 px-3 py-5 sm:px-5" aria-labelledby="feed-heading">
		<div class="mb-4 flex items-baseline justify-between gap-3 px-1">
			<h2 id="feed-heading" class="font-semibold text-ink">Activity across customers</h2>
			<a href={resolve('audit')} class="text-sm text-lapis hover:underline">Filter the full trail</a
			>
		</div>
		<AuditTimeline events={data.feed} showOrganisation linkOrders={false} />
	</section>

	<details class="demo panel xl:sticky xl:top-20" open>
		<summary class="flex cursor-pointer items-center gap-2 px-4 py-3 select-none">
			<Icon name="flask" />
			<span class="font-semibold text-ink">Demo controls</span>
			<span class="ml-auto text-xs text-muted">not in production</span>
			<span class="chev text-muted"><Icon name="chevronDown" size={14} /></span>
		</summary>

		<div class="space-y-6 border-t border-line px-4 py-4">
			<section aria-labelledby="sim-heading">
				<h3 id="sim-heading" class="text-sm font-semibold text-ink">Simulate an agent order</h3>
				<p class="mt-0.5 text-xs text-muted">
					Places an order that needs approval, as if the agent had called <span class="code"
						>place_order</span
					>
					over MCP.
				</p>
				<form method="POST" action="?/simulate" use:enhance class="mt-2 flex gap-2">
					<label for="sim-org" class="sr-only">Buyer organisation</label>
					<select id="sim-org" name="organisationId" class="input min-w-0 flex-1 text-sm">
						{#each data.organisations as o (o.id)}
							<option value={o.id}>{o.name}</option>
						{/each}
					</select>
					<button class="btn btn-sm self-center">Place order</button>
				</form>
				{#if form && 'orderId' in form}
					<p role="status" class="mt-2 text-xs text-ok">
						<span class="code">{form.orderId}</span> is waiting in {form.organisation}’s approval
						inbox.
					</p>
				{/if}
			</section>

			<section aria-labelledby="sc-heading">
				<h3 id="sc-heading" class="text-sm font-semibold text-ink">Stock and price overrides</h3>
				<p class="mt-0.5 text-xs text-muted">
					Applied to live price and availability answers, so exceptions can be shown on demand.
				</p>
				<ul class="mt-2 divide-y divide-line rounded-sm border border-line">
					{#each data.scenarios as sc (sc.id)}
						<li class="flex items-start gap-3 px-3 py-2.5">
							<div class="min-w-0 flex-1">
								<p class="text-sm text-ink">
									<span class="font-medium">{kindLabel[sc.kind]}</span>
									<span class="code text-muted">{sc.productCode}</span>
								</p>
								<p class="truncate text-xs text-muted" title={sc.productName}>{sc.detail}</p>
							</div>
							<form method="POST" action="?/toggle" use:enhance>
								<input type="hidden" name="id" value={sc.id} />
								<input type="hidden" name="active" value={String(!sc.active)} />
								<button
									class="switch"
									role="switch"
									aria-checked={sc.active}
									aria-label="{kindLabel[sc.kind]} for {sc.productCode}"
								>
									<span></span>
								</button>
							</form>
						</li>
					{/each}
				</ul>

				<form method="POST" action="?/add" use:enhance class="mt-3 grid grid-cols-2 gap-2">
					<div>
						<label for="sc-code" class="field-label text-xs">Product code</label>
						<input
							id="sc-code"
							name="productCode"
							class="input code text-sm"
							placeholder="463038"
							inputmode="numeric"
						/>
					</div>
					<div>
						<label for="sc-kind" class="field-label text-xs">What happens</label>
						<select id="sc-kind" name="kind" class="input text-sm">
							{#each Object.entries(kindLabel) as [value, label] (value)}
								<option {value}>{label}</option>
							{/each}
						</select>
					</div>
					<div class="col-span-2">
						<label for="sc-detail" class="field-label text-xs">Detail</label>
						<input
							id="sc-detail"
							name="detail"
							class="input text-sm"
							placeholder="Only 5 KI on Monday"
						/>
					</div>
					{#if form && 'error' in form && form.error}
						<p role="alert" class="col-span-2 text-xs text-stop">{form.error}</p>
					{/if}
					<button class="btn btn-sm col-span-2">Add override</button>
				</form>
			</section>
		</div>
	</details>
</div>

<style>
	.demo {
		border-style: dashed;
		border-color: var(--se-line-strong);
	}
	.demo summary::-webkit-details-marker {
		display: none;
	}
	.demo[open] .chev {
		transform: rotate(180deg);
	}
	.switch {
		position: relative;
		width: 2.25rem;
		height: 1.25rem;
		border-radius: 999px;
		background: var(--se-line-strong);
		transition: background-color 150ms;
		flex-shrink: 0;
		cursor: pointer;
	}
	.switch span {
		position: absolute;
		top: 2px;
		left: 2px;
		width: 1rem;
		height: 1rem;
		border-radius: 50%;
		background: var(--se-panel);
		box-shadow: 0 1px 2px rgb(0 0 0 / 0.25);
		transition: transform 150ms;
	}
	.switch[aria-checked='true'] {
		background: var(--se-lapis);
	}
	.switch[aria-checked='true'] span {
		transform: translateX(1rem);
	}
</style>
