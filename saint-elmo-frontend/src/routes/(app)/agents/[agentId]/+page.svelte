<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import MandateCharter from '#lib/components/domain/MandateCharter.svelte';
	import OutcomeBadge from '#lib/components/app/OutcomeBadge.svelte';
	import TokenReveal from '#lib/components/app/TokenReveal.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Dialog from '#lib/components/ui/dialog/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as RadioGroup from '#lib/components/ui/radio-group/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import * as Tabs from '#lib/components/ui/tabs/index.js';
	import { date, relative } from '#lib/format.js';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	let agent = $derived(data.agent);
	let issued = $derived(form && 'issued' in form ? form.issued : null);
	let showIssue = $state(false);
	let preset = $state('PURCHASING');
	let expires = $state('7');
	// Writable derived: the tabs switch it, and a freshly issued token brings its tab forward.
	let tab = $derived(issued ? 'tokens' : 'mandate');

	const expiryLabel: Record<string, string> = {
		'1': '1 day',
		'7': '7 days',
		'30': '30 days, the maximum'
	};
	const tokenState = (k: (typeof data.keys)[number]) =>
		k.revokedAt ? 'revoked' : new Date(k.expiresAt).getTime() < Date.now() ? 'expired' : 'active';
	let active = $derived(data.keys.filter((k) => tokenState(k) === 'active'));
	let past = $derived(data.keys.filter((k) => tokenState(k) !== 'active'));

	// A new agent arrives here with ?created: say so once, as a toast.
	$effect(() => {
		if (!data.created || !page.url.searchParams.has('created')) return;
		toast.success(`${agent.name} created with mandate v1`, {
			description: 'Issue an Agent token to connect it.'
		});
		const url = new URL(page.url.href);
		url.searchParams.delete('created');
		// eslint-disable-next-line svelte/no-navigation-without-resolve -- same page, only drops ?created
		replaceState(url, page.state);
	});
	$effect(() => {
		if (form && 'revoked' in form) {
			toast(`Token ${form.revoked}… revoked`, {
				description: 'It is refused from the agent’s next request.'
			});
		}
	});
</script>

<svelte:head><title>{agent.name} · Agents · Saint Elmo</title></svelte:head>

<Dialog.Root
	open
	onOpenChange={(open) => {
		if (!open) goto(resolve('agents'), { reset: false });
	}}
>
	<Dialog.Content
		class="top-[6dvh] flex max-h-[min(88dvh,52rem)] translate-y-0 flex-col gap-0 overflow-hidden p-0 sm:top-[8dvh] sm:max-w-3xl"
	>
		<!-- Header: who the agent is, and whether it may act at all -->
		<header
			class="flex flex-wrap items-start justify-between gap-4 border-b px-6 pt-6 pb-5 sm:px-8"
		>
			<div class="min-w-0 pr-8">
				<div class="flex flex-wrap items-center gap-3">
					<Dialog.Title class="code text-xl font-semibold">{agent.name}</Dialog.Title>
					<OutcomeBadge
						outcome={agent.status === 'ACTIVE' ? 'AUTO_APPROVE' : 'REJECT'}
						label={agent.status === 'ACTIVE' ? 'Active' : 'Disabled'}
					/>
				</div>
				<Dialog.Description class="mt-1.5 text-sm">
					{agent.purpose}
					<span class="text-muted-foreground">
						· {agent.lastActiveAt ? `active ${relative(agent.lastActiveAt)}` : 'never used'}</span
					>
				</Dialog.Description>
			</div>
			<form method="POST" action="?/setStatus" use:enhance class="mr-8">
				<input
					type="hidden"
					name="status"
					value={agent.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE'}
				/>
				<Button
					type="submit"
					size="sm"
					variant={agent.status === 'ACTIVE' ? 'destructive' : 'outline'}
				>
					{agent.status === 'ACTIVE' ? 'Disable agent' : 'Enable agent'}
				</Button>
			</form>
		</header>

		<Tabs.Root bind:value={tab} class="flex min-h-0 flex-1 flex-col gap-0">
			<div class="border-b px-6 sm:px-8">
				<Tabs.List variant="line" class="h-11 gap-4">
					<Tabs.Trigger value="mandate">
						Mandate <span class="text-muted-foreground">v{agent.mandate.version}</span>
					</Tabs.Trigger>
					<Tabs.Trigger value="tokens">
						Agent tokens <span class="text-muted-foreground tabular">{active.length}</span>
					</Tabs.Trigger>
				</Tabs.List>
			</div>

			<!-- The mandate, in words, with every rule below it -->
			<Tabs.Content value="mandate" class="min-h-0 flex-1 overflow-y-auto px-6 py-6 sm:px-8">
				<p class="mb-4 text-xs text-muted-foreground">
					Set by a buyer admin. The agent reads it with <span class="code">get_my_mandate</span> and can
					never change it.
				</p>
				<MandateCharter mandate={agent.mandate} periodSpend={agent.periodSpend} rulesOpen />
				{#if agent.status !== 'ACTIVE'}
					<p class="mt-6 rounded-lg bg-stop/8 px-4 py-3 text-sm text-stop">
						Disabled: every token is refused until you enable the agent again.
					</p>
				{/if}
			</Tabs.Content>

			<!-- The credentials that let it act -->
			<Tabs.Content
				value="tokens"
				class="min-h-0 flex-1 space-y-4 overflow-y-auto px-6 py-6 sm:px-8"
			>
				<div class="flex items-center justify-between gap-3">
					<p class="text-sm text-muted-foreground">
						{active.length
							? `${active.length} active. Each names this agent and its mandate, never carries it.`
							: 'No active tokens, so the agent can’t connect.'}
					</p>
					{#if !showIssue && !issued}
						<Button variant="outline" size="sm" onclick={() => (showIssue = true)}>
							<PlusIcon /> Issue
						</Button>
					{/if}
				</div>

				{#if issued}
					<TokenReveal secret={issued.secret} label={issued.key.label} />
				{/if}

				{#if showIssue && !issued}
					<form
						method="POST"
						action="?/issueKey"
						class="rounded-xl border bg-card p-4"
						use:enhance={() =>
							async ({ update, result }) => {
								await update();
								if (result.type === 'success') showIssue = false;
							}}
					>
						<Field.Group class="gap-4">
							<Field.Field>
								<Field.Label for="token-label">Where will it be used?</Field.Label>
								<Input
									id="token-label"
									name="label"
									placeholder="e.g. Claude Desktop, kitchen office"
									required
								/>
							</Field.Field>
							<Field.Set>
								<Field.Label>What it may do</Field.Label>
								<RadioGroup.Root name="preset" bind:value={preset} class="gap-2">
									{#each [['PURCHASING', 'Purchasing', 'Search, quote and place orders.'], ['RESEARCH_ONLY', 'Research only', 'Search and compare, never order.']] as [value, title, hint] (value)}
										<Field.Label
											for="preset-{value}"
											class="rounded-lg border bg-card has-data-[state=checked]:border-primary/50 has-data-[state=checked]:bg-accent/50"
										>
											<Field.Field orientation="horizontal" class="p-3">
												<RadioGroup.Item {value} id="preset-{value}" />
												<Field.Content>
													<Field.Title>{title}</Field.Title>
													<Field.Description>{hint}</Field.Description>
												</Field.Content>
											</Field.Field>
										</Field.Label>
									{/each}
								</RadioGroup.Root>
							</Field.Set>
							<Field.Field>
								<Field.Label for="token-exp">Expires after</Field.Label>
								<Select.Root type="single" name="expiresInDays" bind:value={expires}>
									<Select.Trigger id="token-exp" class="w-full"
										>{expiryLabel[expires]}</Select.Trigger
									>
									<Select.Content>
										{#each Object.entries(expiryLabel) as [value, label] (value)}
											<Select.Item {value} {label} />
										{/each}
									</Select.Content>
								</Select.Root>
							</Field.Field>
						</Field.Group>
						{#if form?.error && form && 'action' in form && form.action === 'issueKey'}
							<p role="alert" class="mt-3 text-sm text-stop">{form.error}</p>
						{/if}
						<div class="mt-4 flex justify-end gap-2">
							<Button type="button" variant="ghost" size="sm" onclick={() => (showIssue = false)}
								>Cancel</Button
							>
							<Button type="submit" size="sm"><KeyRoundIcon /> Issue token</Button>
						</div>
					</form>
				{/if}

				{#if active.length}
					<ul class="divide-y rounded-xl border bg-card">
						{#each active as key (key.jti)}
							<li class="flex items-start gap-3 px-4 py-3">
								<div class="min-w-0 flex-1">
									<p class="truncate text-sm font-medium">{key.label}</p>
									<p class="mt-0.5 text-xs text-muted-foreground">
										<span class="code">{key.prefix}…</span> ·
										{key.scopes.includes('order:place') ? 'Purchasing' : 'Research only'}
									</p>
									<p class="text-xs text-muted-foreground">
										expires {date(key.expiresAt)} ·
										{key.lastUsedAt ? `used ${relative(key.lastUsedAt)}` : 'never used'}
									</p>
								</div>
								<form method="POST" action="?/revokeKey" use:enhance>
									<input type="hidden" name="jti" value={key.jti} />
									<Button type="submit" variant="ghost" size="xs" class="text-stop hover:text-stop"
										>Revoke</Button
									>
								</form>
							</li>
						{/each}
					</ul>
				{/if}

				{#if past.length}
					<details class="group text-xs text-muted-foreground">
						<summary class="cursor-pointer select-none hover:text-foreground">
							{past.length} revoked or expired
						</summary>
						<ul class="mt-2 space-y-1.5">
							{#each past as key (key.jti)}
								<li>
									<span class="line-through">{key.label}</span>
									<span class="code">{key.prefix}…</span>
									· {tokenState(key) === 'revoked' && key.revokedAt
										? `revoked ${relative(key.revokedAt)}`
										: 'expired'}
								</li>
							{/each}
						</ul>
					</details>
				{/if}
			</Tabs.Content>
		</Tabs.Root>
	</Dialog.Content>
</Dialog.Root>
