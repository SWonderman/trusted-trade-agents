<script lang="ts">
	import { resolve } from '$app/paths';
	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';
	import Roundel from '#lib/components/Roundel.svelte';
	import Icon, { type IconName } from '#lib/components/ui/Icon.svelte';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	const POLL_SECONDS = 8;

	let now = $state(Date.now());
	let theme = $state<'light' | 'dark' | null>(null);

	let isStaff = $derived(data.user.role === 'aimo_staff');
	type NavPath = 'inbox' | 'agents' | 'audit' | 'oversight';
	let nav = $derived<{ href: NavPath; label: string; icon: IconName; count?: number }[]>(
		isStaff
			? [
					{ href: 'oversight', label: 'Oversight', icon: 'eye' },
					{ href: 'audit', label: 'Audit trail', icon: 'scroll' }
				]
			: [
					{ href: 'inbox', label: 'Approval inbox', icon: 'inbox', count: data.pending },
					{ href: 'agents', label: 'Agents and mandates', icon: 'agents' },
					{ href: 'audit', label: 'Audit trail', icon: 'scroll' }
				]
	);
	let checkedSecondsAgo = $derived(
		Math.max(0, Math.round((now - new Date(data.checkedAt).getTime()) / 1000))
	);

	// Approvals arrive from agents at any time: poll while the tab is visible.
	// Server-sent events are the next step (design.md §3.4).
	$effect(() => {
		const id = setInterval(() => {
			now = Date.now();
			if (document.visibilityState === 'visible' && checkedSecondsAgo >= POLL_SECONDS) {
				invalidate('app:inbox');
			}
		}, 1000);
		return () => clearInterval(id);
	});

	function toggleTheme() {
		const current =
			theme ??
			(document.documentElement.dataset.theme as 'light' | 'dark' | undefined) ??
			(matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
		theme = current === 'dark' ? 'light' : 'dark';
		document.documentElement.dataset.theme = theme;
		try {
			localStorage.setItem('se-theme', theme);
		} catch {
			// private mode: the choice lasts for this page only
		}
	}

	const isActive = (href: NavPath) =>
		page.url.pathname === `/${href}` || page.url.pathname.startsWith(`/${href}/`);
</script>

<div class="min-h-dvh md:grid md:grid-cols-[15.5rem_1fr]">
	<aside
		class="border-b border-line bg-panel md:sticky md:top-0 md:flex md:h-dvh md:flex-col md:border-r md:border-b-0"
	>
		<div class="flex items-center gap-2.5 px-4 py-3 md:px-5 md:py-5">
			<Roundel size={30} />
			<div class="leading-tight">
				<a href={resolve('/(marketing)')} class="font-serif text-[1.0625rem] font-medium text-ink"
					>Saint Elmo</a
				>
				<p class="text-xs text-muted">Agent control</p>
			</div>
		</div>

		<nav aria-label="Main" class="overflow-x-auto px-2 pb-2 md:flex-1 md:px-3 md:pb-0">
			<ul class="flex gap-1 md:flex-col">
				{#each nav as item (item.href)}
					<li>
						<a
							href={resolve(item.href)}
							aria-current={isActive(item.href) ? 'page' : undefined}
							class={[
								'flex items-center gap-2.5 rounded-sm px-2.5 py-2 text-sm whitespace-nowrap',
								isActive(item.href)
									? 'bg-lapis-wash font-semibold text-lapis'
									: 'text-muted hover:bg-sunken hover:text-ink'
							]}
						>
							<Icon name={item.icon} />
							<span class="flex-1">{item.label}</span>
							{#if item.count}
								<span
									class="tabular rounded-full bg-hold px-1.5 py-px text-xs font-semibold text-white"
									aria-label="{item.count} waiting"
								>
									{item.count}
								</span>
							{/if}
						</a>
					</li>
				{/each}
			</ul>
		</nav>

		<div class="hidden border-t border-line px-5 py-4 md:block">
			<p class="text-xs text-faint">Ordering from</p>
			<img
				src="/brand/valio-aimo-wordmark.png"
				alt="Valio Aimo"
				width="340"
				height="140"
				class="mt-2 h-9 w-auto rounded-sm"
			/>
		</div>
	</aside>

	<div class="min-w-0">
		<header
			class="sticky top-0 z-10 flex h-14 items-center gap-3 border-b border-line bg-panel/90 px-4 backdrop-blur md:px-6"
		>
			<p class="truncate text-sm font-semibold text-ink">
				{data.user.organisation?.name ?? 'Valio Aimo operations'}
			</p>
			{#if data.environment === 'mock'}
				<span
					class="hidden rounded-sm border border-hold/40 px-1.5 py-0.5 text-xs text-hold sm:inline"
					title="Data comes from the in-memory mock, not the backend"
				>
					Demo data
				</span>
			{/if}

			<p class="ml-auto hidden items-center gap-2 text-xs text-muted sm:flex" aria-live="off">
				<span class="live-dot" aria-hidden="true"></span>
				Live, checked {checkedSecondsAgo}s ago
			</p>

			<button
				class="btn btn-quiet btn-sm"
				onclick={toggleTheme}
				aria-label="Switch light or dark theme"
			>
				<Icon name={theme === 'dark' ? 'sun' : 'moon'} />
			</button>

			<details class="relative">
				<summary class="btn btn-quiet btn-sm list-none">
					<span
						class="grid size-6 place-items-center rounded-full bg-lapis-wash text-xs font-semibold text-lapis"
						aria-hidden="true"
					>
						{data.user.name
							.split(' ')
							.map((p) => p[0])
							.join('')}
					</span>
					<span class="hidden sm:inline">{data.user.name}</span>
					<Icon name="chevronDown" size={14} />
				</summary>
				<div
					class="absolute right-0 mt-1 w-64 rounded-md border border-line bg-panel p-2 shadow-lg shadow-black/10"
				>
					<div class="px-2 py-1.5">
						<p class="text-sm font-semibold text-ink">{data.user.name}</p>
						<p class="text-xs text-muted">{data.user.email}</p>
						<p class="mt-1 text-xs text-muted">
							{data.user.role === 'aimo_staff'
								? 'Valio Aimo staff, read-only'
								: 'Buyer admin, can approve orders'}
						</p>
					</div>
					<form method="POST" action="/logout" class="mt-1 border-t border-line pt-1">
						<button class="btn btn-quiet btn-sm w-full justify-start">
							<Icon name="logout" /> Sign out
						</button>
					</form>
				</div>
			</details>
		</header>

		<main class="px-4 py-6 md:px-8 md:py-8">
			{@render children()}
		</main>
	</div>
</div>

<style>
	.live-dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: var(--se-ok);
		box-shadow: 0 0 0 3px color-mix(in srgb, var(--se-ok) 18%, transparent);
	}
	summary::-webkit-details-marker {
		display: none;
	}
</style>
