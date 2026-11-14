<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import MandateSummary from '#lib/components/domain/MandateSummary.svelte';
	import OutcomeBadge from '#lib/components/app/OutcomeBadge.svelte';
	import TokenReveal from '#lib/components/app/TokenReveal.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as RadioGroup from '#lib/components/ui/radio-group/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import * as Sheet from '#lib/components/ui/sheet/index.js';
	import * as Tabs from '#lib/components/ui/tabs/index.js';
	import { date, relative } from '#lib/format.js';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	let agent = $derived(data.agent);
	let issued = $derived(form && 'issued' in form ? form.issued : null);
	let showIssue = $state(false);
	let preset = $state('PURCHASING');
	let expires = $state('7');
	// Writable derived: the tabs can switch it, and a freshly issued token switches it back.
	let tab = $derived(issued ? 'tokens' : 'mandate');

	const expiryLabel: Record<string, string> = {
		'1': '1 day',
		'7': '7 days',
		'30': '30 days, the maximum'
	};
	const tokenState = (k: (typeof data.keys)[number]) =>
		k.revokedAt ? 'revoked' : new Date(k.expiresAt).getTime() < Date.now() ? 'expired' : 'active';
	let activeTokens = $derived(data.keys.filter((k) => tokenState(k) === 'active').length);
</script>

<svelte:head><title>{agent.name} · Agents · Saint Elmo</title></svelte:head>

<Sheet.Root
	open
	onOpenChange={(open) => {
		if (!open) goto(resolve('agents'), { reset: false });
	}}
>
	<Sheet.Content
		side="right"
		class="gap-0 overflow-y-auto data-[side=right]:w-full data-[side=right]:sm:max-w-2xl"
	>
		<Sheet.Header class="border-b px-6 pt-6 pb-5">
			<div class="flex items-center gap-3">
				<Sheet.Title class="code text-lg">{agent.name}</Sheet.Title>
				<OutcomeBadge
					outcome={agent.status === 'ACTIVE' ? 'AUTO_APPROVE' : 'REJECT'}
					label={agent.status === 'ACTIVE' ? 'Active' : 'Disabled'}
				/>
			</div>
			<Sheet.Description>{agent.purpose}</Sheet.Description>
		</Sheet.Header>

		<div class="space-y-6 px-6 py-6">
			{#if data.created}
				<Alert.Root class="border-ok/30 bg-ok/6 text-ok">
					<CircleCheckIcon />
					<Alert.Title class="text-foreground">Agent created with mandate v1</Alert.Title>
					<Alert.Description>Issue an Agent token below to connect it.</Alert.Description>
				</Alert.Root>
			{/if}

			<div class="flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3">
				<p class="text-sm text-muted-foreground">
					{agent.status === 'ACTIVE'
						? 'Its tokens work within the mandate below.'
						: 'Every token is refused until you enable it again.'}
				</p>
				<form method="POST" action="?/setStatus" use:enhance>
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
			</div>

			<Tabs.Root bind:value={tab}>
				<Tabs.List class="w-full">
					<Tabs.Trigger value="mandate">Mandate v{agent.mandate.version}</Tabs.Trigger>
					<Tabs.Trigger value="tokens">
						Agent tokens
						<span class="text-muted-foreground tabular">{activeTokens}</span>
					</Tabs.Trigger>
				</Tabs.List>

				<Tabs.Content value="mandate" class="pt-4">
					<p class="mb-3 text-xs text-muted-foreground">
						Version {agent.mandate.version}. The agent can read it with
						<span class="code">get_my_mandate</span>, never change it.
					</p>
					<MandateSummary mandate={agent.mandate} periodSpend={agent.periodSpend} />
				</Tabs.Content>

				<Tabs.Content value="tokens" class="space-y-4 pt-4">
					{#if issued}
						<TokenReveal secret={issued.secret} label={issued.key.label} />
					{/if}

					{#if showIssue && !issued}
						<form
							method="POST"
							action="?/issueKey"
							class="rounded-xl border bg-muted/40 p-4"
							use:enhance={() =>
								async ({ update, result }) => {
									await update();
									if (result.type === 'success') showIssue = false;
								}}
						>
							<Field.Set>
								<Field.Legend>Issue an Agent token</Field.Legend>
								<Field.Group>
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
										<RadioGroup.Root
											name="preset"
											bind:value={preset}
											class="grid gap-2 sm:grid-cols-2"
										>
											{#each [['PURCHASING', 'Purchasing', 'Search, quote and place orders within the mandate.'], ['RESEARCH_ONLY', 'Research only', 'Search and compare offers, but never order.']] as [value, title, hint] (value)}
												<Field.Label
													for="preset-{value}"
													class="rounded-lg border bg-card has-data-[state=checked]:border-primary/60 has-data-[state=checked]:bg-accent/40"
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
									<Field.Field class="max-w-56">
										<Field.Label for="token-exp">Expires after</Field.Label>
										<Select.Root type="single" name="expiresInDays" bind:value={expires}>
											<Select.Trigger id="token-exp">{expiryLabel[expires]}</Select.Trigger>
											<Select.Content>
												{#each Object.entries(expiryLabel) as [value, label] (value)}
													<Select.Item {value} {label} />
												{/each}
											</Select.Content>
										</Select.Root>
									</Field.Field>
								</Field.Group>
							</Field.Set>
							{#if form?.error && form && 'action' in form && form.action === 'issueKey'}
								<p role="alert" class="mt-3 text-sm text-stop">{form.error}</p>
							{/if}
							<div class="mt-4 flex justify-end gap-2">
								<Button type="button" variant="ghost" onclick={() => (showIssue = false)}
									>Cancel</Button
								>
								<Button type="submit"><KeyRoundIcon /> Issue token</Button>
							</div>
						</form>
					{:else if !issued}
						<Button variant="outline" size="sm" onclick={() => (showIssue = true)}>
							<PlusIcon /> Issue an Agent token
						</Button>
					{/if}

					{#if data.keys.length === 0}
						<p
							class="rounded-xl border border-dashed px-4 py-8 text-center text-sm text-muted-foreground"
						>
							This agent has no tokens, so it can’t connect yet.
						</p>
					{:else}
						<ul class="divide-y rounded-xl border bg-card">
							{#each data.keys as key (key.jti)}
								{@const state = tokenState(key)}
								<li class="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
									<span
										class={[
											'grid size-8 place-items-center rounded-lg',
											state === 'active'
												? 'bg-primary/10 text-primary'
												: 'bg-muted text-muted-foreground'
										]}
									>
										<KeyRoundIcon class="size-4" aria-hidden="true" />
									</span>
									<div class="min-w-0 flex-1">
										<p class="flex flex-wrap items-center gap-2 text-sm">
											<span
												class={[
													'font-medium',
													state !== 'active' && 'text-muted-foreground line-through'
												]}>{key.label}</span
											>
											<span class="code text-muted-foreground">{key.prefix}…</span>
										</p>
										<p class="mt-0.5 text-xs text-muted-foreground">
											{key.scopes.includes('order:place') ? 'Purchasing' : 'Research only'} · issued by
											{key.createdBy}
											{relative(key.createdAt)} ·
											{state === 'revoked'
												? `revoked ${relative(key.revokedAt!)}`
												: state === 'expired'
													? 'expired'
													: `expires ${date(key.expiresAt)}`}
											· {key.lastUsedAt ? `last used ${relative(key.lastUsedAt)}` : 'never used'}
										</p>
									</div>
									{#if state === 'active'}
										<form method="POST" action="?/revokeKey" use:enhance>
											<input type="hidden" name="jti" value={key.jti} />
											<Button type="submit" variant="destructive" size="sm">Revoke</Button>
										</form>
									{:else}
										<span class="text-xs text-muted-foreground"
											>{state === 'revoked' ? 'Revoked' : 'Expired'}</span
										>
									{/if}
								</li>
							{/each}
						</ul>
					{/if}
					{#if form && 'revoked' in form}
						<p role="status" class="text-sm text-muted-foreground">
							Revoked <span class="code">{form.revoked}</span>. It’s refused from the agent’s next
							request.
						</p>
					{/if}
				</Tabs.Content>
			</Tabs.Root>
		</div>
	</Sheet.Content>
</Sheet.Root>
