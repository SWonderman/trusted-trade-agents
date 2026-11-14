<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import MandateSummary from '#lib/components/domain/MandateSummary.svelte';
	import Drawer from '#lib/components/ui/Drawer.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import KeyReveal from '#lib/components/ui/KeyReveal.svelte';
	import OutcomeBadge from '#lib/components/ui/OutcomeBadge.svelte';
	import { date, relative } from '#lib/format.js';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	let agent = $derived(data.agent);
	let issued = $derived(form && 'issued' in form ? form.issued : null);
	let showIssue = $state(false);

	const keyState = (k: (typeof data.keys)[number]) =>
		k.revokedAt ? 'revoked' : new Date(k.expiresAt).getTime() < Date.now() ? 'expired' : 'active';
</script>

<svelte:head><title>{agent.name} · Agents · Saint Elmo</title></svelte:head>

<Drawer
	title={agent.name}
	description={agent.purpose}
	width="40rem"
	onclose={() => goto(resolve('agents'), { reset: false })}
>
	{#if data.created}
		<p
			role="status"
			class="mb-5 rounded-md border border-ok/30 bg-ok-wash px-4 py-3 text-sm text-ok"
		>
			Agent created with mandate v1. Issue a key below to connect it.
		</p>
	{/if}

	<section
		class="flex flex-wrap items-center justify-between gap-3 rounded-md border border-line px-4 py-3"
	>
		<div class="flex items-center gap-3">
			<OutcomeBadge
				outcome={agent.status === 'ACTIVE' ? 'AUTO_APPROVE' : 'REJECT'}
				label={agent.status === 'ACTIVE' ? 'Active' : 'Disabled'}
			/>
			<p class="text-sm text-muted">
				{agent.status === 'ACTIVE'
					? 'Its keys work within the mandate below.'
					: 'Every key is refused until you enable it again.'}
			</p>
		</div>
		<form method="POST" action="?/setStatus" use:enhance>
			<input
				type="hidden"
				name="status"
				value={agent.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'}
			/>
			<button class={['btn btn-sm', agent.status === 'ACTIVE' && 'btn-danger']}>
				{agent.status === 'ACTIVE' ? 'Disable agent' : 'Enable agent'}
			</button>
		</form>
	</section>

	<section class="mt-7" aria-labelledby="mandate-heading">
		<div class="mb-3 flex items-baseline justify-between">
			<h3 id="mandate-heading" class="text-base font-semibold text-ink">Mandate</h3>
			<p class="text-xs text-muted">Version {agent.mandate.version}, readable by the agent</p>
		</div>
		<MandateSummary mandate={agent.mandate} periodSpend={agent.periodSpend} />
	</section>

	<section class="mt-8 border-t border-line pt-6" aria-labelledby="keys-heading">
		<div class="mb-3 flex items-center justify-between gap-3">
			<h3 id="keys-heading" class="text-base font-semibold text-ink">Agent keys</h3>
			{#if !showIssue && !issued}
				<button id="issue-key" class="btn btn-sm" onclick={() => (showIssue = true)}
					><Icon name="key" /> Issue a key</button
				>
			{/if}
		</div>

		{#if issued}
			<div class="mb-4"><KeyReveal secret={issued.secret} label={issued.key.label} /></div>
		{/if}

		{#if showIssue && !issued}
			<form
				method="POST"
				action="?/issueKey"
				class="mb-5 space-y-4 rounded-md border border-line bg-surface p-4"
				use:enhance={() =>
					async ({ update, result }) => {
						await update();
						if (result.type === 'success') showIssue = false;
					}}
			>
				<div>
					<label for="key-label" class="field-label">Where will it be used?</label>
					<input
						id="key-label"
						name="label"
						class="input"
						placeholder="e.g. Claude Desktop, kitchen office"
						required
					/>
				</div>
				<fieldset>
					<legend class="field-label">What it may do</legend>
					<div class="grid gap-2 sm:grid-cols-2">
						<label
							class="flex gap-2.5 rounded-sm border border-line bg-panel p-3 text-sm has-checked:border-lapis"
						>
							<input type="radio" name="preset" value="PURCHASING" checked class="mt-0.5" />
							<span>
								<span class="font-semibold text-ink">Purchasing</span>
								<span class="block text-muted"
									>Search, quote and place orders within the mandate.</span
								>
							</span>
						</label>
						<label
							class="flex gap-2.5 rounded-sm border border-line bg-panel p-3 text-sm has-checked:border-lapis"
						>
							<input type="radio" name="preset" value="RESEARCH_ONLY" class="mt-0.5" />
							<span>
								<span class="font-semibold text-ink">Research only</span>
								<span class="block text-muted">Search and compare offers, but never order.</span>
							</span>
						</label>
					</div>
				</fieldset>
				<div class="max-w-48">
					<label for="key-exp" class="field-label">Expires after</label>
					<select id="key-exp" name="expiresInDays" class="input">
						<option value="1">1 day</option>
						<option value="7" selected>7 days</option>
						<option value="30">30 days, the maximum</option>
					</select>
				</div>
				{#if form?.error && form && 'action' in form && form.action === 'issueKey'}
					<p role="alert" class="text-sm text-stop">{form.error}</p>
				{/if}
				<div class="flex justify-end gap-2">
					<button type="button" class="btn btn-quiet" onclick={() => (showIssue = false)}
						>Cancel</button
					>
					<button class="btn btn-primary">Issue key</button>
				</div>
			</form>
		{/if}

		{#if data.keys.length === 0}
			<p
				class="rounded-md border border-dashed border-line-strong px-4 py-6 text-center text-sm text-muted"
			>
				This agent has no keys, so it can’t connect yet.
			</p>
		{:else}
			<ul class="divide-y divide-line rounded-md border border-line">
				{#each data.keys as key (key.jti)}
					{@const state = keyState(key)}
					<li class="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
						<div class="min-w-0 flex-1">
							<p class="flex flex-wrap items-center gap-2">
								<span class="font-medium text-ink">{key.label}</span>
								<span class="code text-muted">{key.prefix}…</span>
							</p>
							<p class="mt-0.5 text-xs text-muted">
								{key.scopes.includes('order:place') ? 'Purchasing' : 'Research only'}, issued by
								{key.createdBy}
								{relative(key.createdAt)},
								{state === 'revoked'
									? `revoked ${relative(key.revokedAt!)}`
									: state === 'expired'
										? 'expired'
										: `expires ${date(key.expiresAt)}`}.
								{key.lastUsedAt ? `Last used ${relative(key.lastUsedAt)}.` : 'Never used.'}
							</p>
						</div>
						{#if state === 'active'}
							<form method="POST" action="?/revokeKey" use:enhance>
								<input type="hidden" name="jti" value={key.jti} />
								<button class="btn btn-danger btn-sm">Revoke</button>
							</form>
						{:else}
							<span class="text-xs text-faint">{state === 'revoked' ? 'Revoked' : 'Expired'}</span>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
		{#if form && 'revoked' in form}
			<p role="status" class="mt-2 text-sm text-muted">
				Revoked <span class="code">{form.revoked}</span>. It’s refused from the agent’s next
				request.
			</p>
		{/if}
	</section>
</Drawer>
