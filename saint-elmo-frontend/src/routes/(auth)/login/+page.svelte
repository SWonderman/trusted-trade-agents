<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import ShieldCheckIcon from '@lucide/svelte/icons/shield-check';
	import Roundel from '#lib/components/Roundel.svelte';
	import * as Alert from '#lib/components/ui/alert/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import { Label } from '#lib/components/ui/label/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	let email = $state('');
	let password = $state('');
	let submitting = $state(false);
	let secure = $derived(page.url.protocol === 'https:' || page.url.hostname === 'localhost');
</script>

<svelte:head><title>Sign in · Saint Elmo</title></svelte:head>

<div class="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
	<main class="flex flex-col px-6 py-8 sm:px-12">
		<a href={resolve('/(marketing)')} class="flex w-fit items-center gap-2.5">
			<Roundel size={34} />
			<span class="font-display text-[1.375rem] font-medium tracking-tight">Saint Elmo</span>
		</a>

		<div class="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-12">
			<h1 class="font-display-tight text-[2.5rem]">Sign in to agent control</h1>
			<p class="mt-3 text-sm text-pretty text-muted-foreground">
				Approve what your purchasing agents can’t decide alone, and set the limits they work within.
			</p>

			<form
				method="POST"
				class="mt-8 space-y-4"
				use:enhance={() => {
					submitting = true;
					return async ({ update }) => {
						await update({ reset: false });
						submitting = false;
					};
				}}
			>
				<div class="space-y-1.5">
					<Label for="email">Work email</Label>
					<Input
						id="email"
						name="email"
						type="email"
						autocomplete="username"
						required
						class="h-10"
						bind:value={email}
						aria-invalid={form?.error ? 'true' : undefined}
						aria-describedby={form?.error ? 'login-error' : undefined}
					/>
				</div>
				<div class="space-y-1.5">
					<Label for="password">Password</Label>
					<Input
						id="password"
						name="password"
						type="password"
						autocomplete="current-password"
						required
						class="h-10"
						bind:value={password}
						aria-invalid={form?.error ? 'true' : undefined}
					/>
				</div>

				{#if form?.error}
					<Alert.Root variant="destructive" id="login-error" role="alert">
						<CircleAlertIcon />
						<Alert.Title>{form.error}</Alert.Title>
					</Alert.Root>
				{/if}

				<Button type="submit" size="lg" class="h-10 w-full" disabled={submitting}>
					{#if submitting}<Spinner /> Signing in…{:else}Sign in{/if}
				</Button>
			</form>

			<div class="mt-6 grid grid-cols-2 gap-2">
				<Button variant="outline" disabled aria-describedby="sso-note">
					<ShieldCheckIcon /> Single sign-on
				</Button>
				<Button variant="outline" disabled aria-describedby="sso-note">
					<KeyRoundIcon /> Passkey
				</Button>
			</div>
			<p id="sso-note" class="mt-2 text-xs text-muted-foreground">
				Single sign-on and passkeys aren’t available in the demo.
			</p>

			{#if data.demoAccounts.length}
				<section class="mt-8 rounded-xl border bg-card p-3" aria-labelledby="demo-accounts">
					<h2 id="demo-accounts" class="px-2 pt-1 text-sm font-medium">Demo accounts</h2>
					<p class="px-2 text-xs text-muted-foreground">Choose one to fill in the form.</p>
					<ul class="mt-2">
						{#each data.demoAccounts as account (account.email)}
							<li>
								<button
									type="button"
									class="flex w-full flex-col rounded-lg px-2 py-1.5 text-left text-sm hover:bg-muted"
									onclick={() => {
										email = account.email;
										password = account.password;
									}}
								>
									<span>{account.label}</span>
									<span class="code text-xs text-muted-foreground">{account.email}</span>
								</button>
							</li>
						{/each}
					</ul>
				</section>
			{/if}
		</div>

		<ul class="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
			<li class="flex items-center gap-1.5">
				<span class={['size-1.5 rounded-full', secure ? 'bg-ok' : 'bg-hold']} aria-hidden="true"
				></span>
				{secure ? 'Encrypted connection' : 'Connection is not encrypted'}
			</li>
			<li class="flex items-center gap-1.5">
				<span
					class={['size-1.5 rounded-full', data.environment === 'live' ? 'bg-ok' : 'bg-hold']}
					aria-hidden="true"
				></span>
				{data.environment === 'live'
					? 'Signs in with the Saint Elmo backend'
					: 'Demo sign-in with built-in accounts'}
			</li>
			<li>Sessions last 60 minutes. Agents can never sign in here.</li>
		</ul>
	</main>

	<aside
		class="relative hidden overflow-hidden bg-lapis-night lg:block"
		aria-label="About Saint Elmo"
	>
		<img
			src="/art/erasmus-plate-1600.webp"
			alt="Saint Erasmus in bishop’s robes, from Matthias Grünewald’s panel"
			class="absolute inset-0 size-full object-cover object-[50%_18%] opacity-90"
		/>
		<div
			class="absolute inset-0 bg-linear-to-t from-lapis-night via-lapis-night/40 to-transparent"
		></div>
		<figure class="absolute inset-x-0 bottom-0 p-12 text-vellum">
			<blockquote class="max-w-md font-display text-3xl leading-tight text-balance">
				Agents do the ordering. <em class="text-gold">People keep the deciding.</em>
			</blockquote>
			<figcaption class="mt-4 text-xs text-vellum/60">
				Matthias Grünewald, <em>The Meeting of Saint Erasmus and Saint Maurice</em>, c. 1520–24.
				Alte Pinakothek, Munich.
			</figcaption>
		</figure>
	</aside>
</div>
