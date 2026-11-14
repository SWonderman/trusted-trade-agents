<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import AuditTimeline from '#lib/components/domain/AuditTimeline.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	let filtered = $derived(
		Boolean(data.filter.agentId || data.filter.orderId || data.filter.type || data.filter.outcome)
	);
</script>

<svelte:head><title>Audit trail · Saint Elmo</title></svelte:head>

<div class="mb-6 flex flex-wrap items-end justify-between gap-4">
	<div>
		<h1 class="text-2xl font-semibold tracking-tight text-ink">Audit trail</h1>
		<p class="mt-1 max-w-[64ch] text-sm text-muted">
			Every tool call, policy decision, approval and key change, newest first. Entries are only ever
			added, and each one carries the hash of the entry before it, so edited history can be
			detected.
			{data.crossCustomer
				? 'You are seeing every buyer organisation.'
				: 'Valio Aimo sees the same entries.'}
		</p>
	</div>
	<a href="{resolve('audit/export.json')}{page.url.search}" class="btn btn-sm" download
		>Download as JSON</a
	>
</div>

<form
	method="GET"
	class="panel mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_1fr_auto]"
	data-sveltekit-keepfocus
>
	<div>
		<label for="f-agent" class="field-label">Agent</label>
		<select id="f-agent" name="agent" class="input">
			<option value="">All agents</option>
			{#each data.agentOptions as a (a.id)}
				<option value={a.id} selected={data.filter.agentId === a.id}>{a.name}</option>
			{/each}
		</select>
	</div>
	<div>
		<label for="f-order" class="field-label">Order or quote</label>
		<input
			id="f-order"
			name="order"
			class="input code"
			placeholder="ORD-0142"
			value={data.filter.orderId ?? ''}
		/>
	</div>
	<div>
		<label for="f-type" class="field-label">Tool call or event</label>
		<select id="f-type" name="type" class="input">
			<option value="">Everything</option>
			{#each data.typeOptions as t (t)}
				<option value={t} selected={data.filter.type === t}>{t}</option>
			{/each}
		</select>
	</div>
	<div>
		<label for="f-outcome" class="field-label">Policy outcome</label>
		<select id="f-outcome" name="outcome" class="input">
			<option value="">Any</option>
			<option value="AUTO_APPROVE" selected={data.filter.outcome === 'AUTO_APPROVE'}
				>Auto-approved</option
			>
			<option value="NEEDS_HUMAN" selected={data.filter.outcome === 'NEEDS_HUMAN'}
				>Needs approval</option
			>
			<option value="REJECT" selected={data.filter.outcome === 'REJECT'}>Rejected by policy</option>
		</select>
	</div>
	<div class="flex items-end gap-2">
		<button class="btn btn-primary">Filter</button>
		{#if filtered}<a href={resolve('audit')} class="btn btn-quiet">Clear</a>{/if}
	</div>
</form>

<div class="mb-4 flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
	<p class="tabular">
		{filtered ? `${data.events.length} of ${data.total} entries` : `${data.events.length} entries`}
	</p>
	<p class="flex flex-wrap items-center gap-4" aria-hidden="true">
		<span class="flex items-center gap-1.5"><span class="legend agent"></span>Agent</span>
		<span class="flex items-center gap-1.5"><span class="legend user"></span>Person</span>
		<span class="flex items-center gap-1.5"><span class="legend system"></span>System</span>
	</p>
</div>

{#if data.events.length === 0}
	<div class="panel px-6 py-10 text-center">
		<p class="font-semibold text-ink">No entries match these filters</p>
		<p class="mt-1 text-sm text-muted">
			Check the order id, or clear the filters to see the whole trail.
		</p>
		<a href={resolve('audit')} class="btn mt-4">Clear filters</a>
	</div>
{:else}
	<div class="panel px-3 py-5 sm:px-5">
		<AuditTimeline
			events={data.events}
			showOrganisation={data.crossCustomer}
			linkOrders={!data.crossCustomer}
		/>
	</div>
{/if}

<style>
	.legend {
		display: inline-block;
		width: 0.625rem;
		height: 0.625rem;
		border-radius: 50%;
	}
	.legend.agent {
		border: 2px solid var(--se-lapis);
	}
	.legend.user {
		background: var(--se-ink);
	}
	.legend.system {
		width: 0.375rem;
		height: 0.375rem;
		background: var(--se-faint);
	}
</style>
