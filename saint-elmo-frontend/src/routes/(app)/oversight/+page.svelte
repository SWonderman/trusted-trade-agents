<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import AuditTimeline from '#lib/components/domain/AuditTimeline.svelte';
	import PageHeader from '#lib/components/app/PageHeader.svelte';
	import { Badge } from '#lib/components/ui/badge/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Card from '#lib/components/ui/card/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import { Switch } from '#lib/components/ui/switch/index.js';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const kindLabel = {
		OUT_OF_STOCK: 'Out of stock',
		PARTIAL: 'Partial stock',
		LATE: 'Late delivery',
		PRICE_CHANGE: 'Price change'
	} as const;
	let simOrg = $derived(data.organisations[0]?.id ?? '');
	let kind = $state<keyof typeof kindLabel>('OUT_OF_STOCK');

	let stats = $derived([
		['Buyer organisations', data.stats.organisations],
		['Tool calls, 24 h', data.stats.toolCalls],
		['Orders placed, 24 h', data.stats.ordersPlaced],
		['Sent to a person, 24 h', data.stats.waiting],
		['Rejected by policy, 24 h', data.stats.rejected]
	] as const);
</script>

<svelte:head><title>Oversight · Saint Elmo</title></svelte:head>

<PageHeader
	title="Oversight"
	source={data.source}
	description="What every buyer organisation’s agents are doing with Valio Aimo, as it happens. You can read this trail but not approve, reject or change anything for a customer."
>
	{#snippet actions()}
		<Badge variant="outline">Read-only</Badge>
	{/snippet}
</PageHeader>

<dl class="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
	{#each stats as [label, value] (label)}
		<div class="rounded-xl border bg-card px-4 py-3">
			<dt class="text-xs text-muted-foreground">{label}</dt>
			<dd class="mt-1 text-2xl font-semibold tracking-tight tabular">{value}</dd>
		</div>
	{/each}
</dl>

<div class="grid items-start gap-6 xl:grid-cols-[1fr_23rem]">
	<section
		class="min-w-0 rounded-xl border bg-card px-3 py-5 sm:px-6"
		aria-labelledby="feed-heading"
	>
		<div class="mb-4 flex items-baseline justify-between gap-3">
			<h2 id="feed-heading" class="font-semibold">Activity across customers</h2>
			<Button href={resolve('audit')} variant="link" size="sm" class="px-0"
				>Filter the full trail</Button
			>
		</div>
		<AuditTimeline events={data.feed} showOrganisation linkOrders={false} />
	</section>

	<Card.Root class="border-dashed xl:sticky xl:top-20">
		<Card.Header>
			<Card.Title class="flex items-center gap-2"
				><FlaskConicalIcon class="size-4" /> Demo controls</Card.Title
			>
			<Card.Description>Not in production.</Card.Description>
		</Card.Header>
		<Card.Content class="space-y-7">
			<section aria-labelledby="sim-heading">
				<h3 id="sim-heading" class="text-sm font-medium">Simulate an agent order</h3>
				<p class="mt-0.5 text-xs text-muted-foreground">
					Places an order that needs approval, as if the agent had called
					<span class="code">place_order</span> over MCP.
				</p>
				<form method="POST" action="?/simulate" use:enhance class="mt-3 flex gap-2">
					<Select.Root type="single" name="organisationId" bind:value={simOrg}>
						<Select.Trigger class="min-w-0 flex-1" aria-label="Buyer organisation">
							{data.organisations.find((o) => o.id === simOrg)?.name ?? 'Choose'}
						</Select.Trigger>
						<Select.Content>
							{#each data.organisations as o (o.id)}
								<Select.Item value={o.id} label={o.name} />
							{/each}
						</Select.Content>
					</Select.Root>
					<Button type="submit" variant="outline">Place order</Button>
				</form>
				{#if form && 'orderId' in form}
					<p role="status" class="mt-2 text-xs text-ok">
						<span class="code">{form.orderId}</span> is waiting in {form.organisation}’s approvals.
					</p>
				{/if}
			</section>

			<section aria-labelledby="sc-heading">
				<h3 id="sc-heading" class="text-sm font-medium">Stock and price overrides</h3>
				<p class="mt-0.5 text-xs text-muted-foreground">
					Applied to live price and availability answers, so exceptions can be shown on demand.
				</p>
				<ul class="mt-3 divide-y rounded-lg border">
					{#each data.scenarios as sc (sc.id)}
						<li class="flex items-center gap-3 px-3 py-2.5">
							<div class="min-w-0 flex-1">
								<p class="text-sm">
									<span class="font-medium">{kindLabel[sc.kind]}</span>
									<span class="code text-muted-foreground">{sc.productCode}</span>
								</p>
								<p class="truncate text-xs text-muted-foreground" title={sc.productName}>
									{sc.detail}
								</p>
							</div>
							<form method="POST" action="?/toggle" use:enhance>
								<input type="hidden" name="id" value={sc.id} />
								<input type="hidden" name="active" value={String(!sc.active)} />
								<Switch
									type="submit"
									checked={sc.active}
									aria-label="{kindLabel[sc.kind]} for {sc.productCode}"
								/>
							</form>
						</li>
					{/each}
				</ul>

				<form method="POST" action="?/add" use:enhance class="mt-4 grid grid-cols-2 gap-3">
					<div class="space-y-1.5">
						<Label for="sc-code" class="text-xs">Product code</Label>
						<Input
							id="sc-code"
							name="productCode"
							class="code"
							placeholder="463038"
							inputmode="numeric"
						/>
					</div>
					<div class="space-y-1.5">
						<Label for="sc-kind" class="text-xs">What happens</Label>
						<Select.Root type="single" name="kind" bind:value={kind}>
							<Select.Trigger id="sc-kind" class="w-full">{kindLabel[kind]}</Select.Trigger>
							<Select.Content>
								{#each Object.entries(kindLabel) as [value, label] (value)}
									<Select.Item {value} {label} />
								{/each}
							</Select.Content>
						</Select.Root>
					</div>
					<div class="col-span-2 space-y-1.5">
						<Label for="sc-detail" class="text-xs">Detail</Label>
						<Input id="sc-detail" name="detail" placeholder="Only 5 KI on Monday" />
					</div>
					{#if form && 'error' in form && form.error}
						<p role="alert" class="col-span-2 text-xs text-stop">{form.error}</p>
					{/if}
					<Button type="submit" variant="outline" class="col-span-2">Add override</Button>
				</form>
			</section>
		</Card.Content>
	</Card.Root>
</div>
