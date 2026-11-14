<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import { page } from '$app/state';
	import Roundel from '#lib/components/Roundel.svelte';
	import Icon from '#lib/components/ui/Icon.svelte';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	let email = $state('');
	let password = $state('');
	let submitting = $state(false);
	let secure = $derived(page.url.protocol === 'https:' || page.url.hostname === 'localhost');
</script>

<svelte:head><title>Sign in · Saint Elmo</title></svelte:head>

<main class="grid min-h-dvh place-items-center px-4 py-12">
	<div class="w-full max-w-[25rem]">
		<a href={resolve('/(marketing)')} class="mb-8 flex items-center gap-3 text-ink no-underline">
			<Roundel size={40} />
			<span class="font-serif text-2xl font-medium tracking-tight">Saint Elmo</span>
		</a>

		<div class="panel p-6 sm:p-8">
			<h1 class="text-xl font-semibold text-ink">Sign in to agent control</h1>
			<p class="mt-1.5 text-sm text-muted">
				Approve what your purchasing agents can’t decide alone, and set the limits they work within.
			</p>

			<form
				method="POST"
				class="mt-6 space-y-4"
				use:enhance={() => {
					submitting = true;
					return async ({ update }) => {
						await update({ reset: false });
						submitting = false;
					};
				}}
			>
				<div>
					<label class="field-label" for="email">Work email</label>
					<input
						id="email"
						name="email"
						type="email"
						autocomplete="username"
						required
						class="input"
						bind:value={email}
						aria-describedby={form?.error ? 'login-error' : undefined}
					/>
				</div>
				<div>
					<label class="field-label" for="password">Password</label>
					<input
						id="password"
						name="password"
						type="password"
						autocomplete="current-password"
						required
						class="input"
						bind:value={password}
					/>
				</div>

				{#if form?.error}
					<p
						id="login-error"
						role="alert"
						class="rounded-sm bg-stop-wash px-3 py-2 text-sm text-stop"
					>
						{form.error}
					</p>
				{/if}

				<button class="btn btn-primary w-full" disabled={submitting}>
					{submitting ? 'Signing in…' : 'Sign in'}
				</button>
			</form>

			<div class="mt-5 grid grid-cols-2 gap-2">
				<button class="btn" disabled aria-describedby="sso-note">
					<Icon name="shield" /> Single sign-on
				</button>
				<button class="btn" disabled aria-describedby="sso-note">
					<Icon name="key" /> Passkey
				</button>
			</div>
			<p id="sso-note" class="mt-2 text-xs text-faint">
				Single sign-on and passkeys aren’t available in the demo.
			</p>
		</div>

		<dl class="mt-5 space-y-2 px-1 text-[0.8125rem] text-muted">
			<div class="flex items-center gap-2">
				<span class={['size-2 rounded-full', secure ? 'bg-ok' : 'bg-hold']}></span>
				<dt class="sr-only">Connection</dt>
				<dd>{secure ? 'Encrypted connection' : 'Connection is not encrypted'}</dd>
			</div>
			<div class="flex items-center gap-2">
				<span class={['size-2 rounded-full', data.environment === 'live' ? 'bg-ok' : 'bg-hold']}
				></span>
				<dt class="sr-only">Environment</dt>
				<dd>
					{data.environment === 'live'
						? 'Connected to the Saint Elmo backend'
						: 'Demo environment with synthetic data'}
				</dd>
			</div>
			<div class="flex items-center gap-2">
				<span class="size-2 rounded-full bg-line-strong"></span>
				<dt class="sr-only">Session</dt>
				<dd>Sessions last 60 minutes. Agents can never sign in here.</dd>
			</div>
		</dl>

		{#if data.demoAccounts.length}
			<section class="mt-8 border-t border-line pt-5" aria-labelledby="demo-accounts">
				<h2 id="demo-accounts" class="text-[0.8125rem] font-semibold text-ink">Demo accounts</h2>
				<p class="mt-0.5 text-[0.8125rem] text-muted">
					Choose one to fill in the form. The password is “demo”.
				</p>
				<ul class="mt-3 space-y-1">
					{#each data.demoAccounts as account (account.email)}
						<li>
							<button
								type="button"
								class="flex w-full items-baseline justify-between gap-3 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-sunken"
								onclick={() => {
									email = account.email;
									password = account.password;
								}}
							>
								<span class="text-ink">{account.label}</span>
								<span class="code text-faint">{account.email}</span>
							</button>
						</li>
					{/each}
				</ul>
			</section>
		{/if}
	</div>
</main>
