<script lang="ts">
	import { resolve } from '$app/paths';
	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';
	import { toggleMode } from 'mode-watcher';
	import MoonIcon from '@lucide/svelte/icons/moon';
	import SunIcon from '@lucide/svelte/icons/sun';
	import AppSidebar from '#lib/components/app/AppSidebar.svelte';
	import * as Breadcrumb from '#lib/components/ui/breadcrumb/index.js';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Separator } from '#lib/components/ui/separator/index.js';
	import * as Sidebar from '#lib/components/ui/sidebar/index.js';
	import * as Tooltip from '#lib/components/ui/tooltip/index.js';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();

	const POLL_SECONDS = 8;
	const sections: Record<string, string> = {
		inbox: 'Approvals',
		agents: 'Agents & mandates',
		catalog: 'Catalog',
		audit: 'Audit trail',
		oversight: 'Oversight'
	};

	let now = $state(Date.now());
	let checkedSecondsAgo = $derived(
		Math.max(0, Math.round((now - new Date(data.checkedAt).getTime()) / 1000))
	);
	let crumbs = $derived(page.url.pathname.split('/').filter(Boolean));
	let section = $derived(crumbs[0] ?? '');

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
</script>

<Sidebar.Provider>
	<AppSidebar user={data.user} pending={data.pending} modes={data.modes} />
	<Sidebar.Inset class="min-w-0">
		<header
			class="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-2 border-b border-border/70 bg-background/85 px-4 backdrop-blur-md md:rounded-t-xl md:px-6"
		>
			<Sidebar.Trigger class="-ml-1.5" />
			<Separator orientation="vertical" class="mr-1 data-[orientation=vertical]:h-4" />
			<Breadcrumb.Root>
				<Breadcrumb.List>
					<Breadcrumb.Item>
						{#if crumbs.length > 1}
							<Breadcrumb.Link href={resolve(section as 'inbox')}
								>{sections[section] ?? section}</Breadcrumb.Link
							>
						{:else}
							<Breadcrumb.Page>{sections[section] ?? section}</Breadcrumb.Page>
						{/if}
					</Breadcrumb.Item>
					{#if crumbs[1]}
						<Breadcrumb.Separator />
						<Breadcrumb.Item>
							<Breadcrumb.Page class={crumbs[1] === 'new' ? '' : 'code'}>
								{crumbs[1] === 'new' ? 'New agent' : decodeURIComponent(crumbs[1])}
							</Breadcrumb.Page>
						</Breadcrumb.Item>
					{/if}
				</Breadcrumb.List>
			</Breadcrumb.Root>

			<div class="ml-auto flex items-center gap-1">
				<p
					class="mr-2 hidden items-center gap-2 text-xs text-muted-foreground sm:flex"
					aria-live="off"
				>
					<span class="relative flex size-2" aria-hidden="true">
						<span class="absolute inline-flex size-full animate-ping rounded-full bg-ok/50"></span>
						<span class="relative inline-flex size-2 rounded-full bg-ok"></span>
					</span>
					<span class="tabular">Checked {checkedSecondsAgo}s ago</span>
				</p>
				<Tooltip.Root>
					<Tooltip.Trigger>
						{#snippet child({ props })}
							<Button
								{...props}
								variant="ghost"
								size="icon-sm"
								onclick={toggleMode}
								aria-label="Switch light or dark theme"
							>
								<SunIcon class="hidden dark:block" />
								<MoonIcon class="dark:hidden" />
							</Button>
						{/snippet}
					</Tooltip.Trigger>
					<Tooltip.Content>Light or dark</Tooltip.Content>
				</Tooltip.Root>
			</div>
		</header>

		<main class="mx-auto w-full max-w-[90rem] flex-1 px-4 py-8 md:px-8 md:py-10">
			{@render children()}
		</main>
	</Sidebar.Inset>
</Sidebar.Provider>
