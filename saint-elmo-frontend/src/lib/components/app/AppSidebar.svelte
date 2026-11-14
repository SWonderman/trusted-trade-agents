<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import BookOpenIcon from '@lucide/svelte/icons/book-open';
	import BotIcon from '@lucide/svelte/icons/bot';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import EyeIcon from '@lucide/svelte/icons/eye';
	import InboxIcon from '@lucide/svelte/icons/inbox';
	import LogOutIcon from '@lucide/svelte/icons/log-out';
	import ScrollTextIcon from '@lucide/svelte/icons/scroll-text';
	import Roundel from '#lib/components/Roundel.svelte';
	import * as Avatar from '#lib/components/ui/avatar/index.js';
	import * as DropdownMenu from '#lib/components/ui/dropdown-menu/index.js';
	import * as Sidebar from '#lib/components/ui/sidebar/index.js';
	import type { SessionUser } from '#lib/api/types.js';

	type Area = 'auth' | 'catalog' | 'orders' | 'agents' | 'audit' | 'oversight';

	let {
		user,
		pending,
		modes
	}: { user: SessionUser; pending: number; modes: Record<Area, 'mock' | 'http'> } = $props();

	let isStaff = $derived(user.role === 'AIMO_STAFF');
	type NavPath = 'inbox' | 'agents' | 'catalog' | 'audit' | 'oversight';
	type Item = { href: NavPath; label: string; icon: typeof InboxIcon; count?: number };

	let work = $derived<Item[]>(
		isStaff
			? [{ href: 'oversight', label: 'Oversight', icon: EyeIcon }]
			: [
					{ href: 'inbox', label: 'Approvals', icon: InboxIcon, count: pending },
					{ href: 'agents', label: 'Agents & mandates', icon: BotIcon }
				]
	);
	const reference: Item[] = [
		{ href: 'catalog', label: 'Catalog', icon: BookOpenIcon },
		{ href: 'audit', label: 'Audit trail', icon: ScrollTextIcon }
	];

	const isActive = (href: NavPath) =>
		page.url.pathname === `/${href}` || page.url.pathname.startsWith(`/${href}/`);

	let initials = $derived(
		user.name
			.split(' ')
			.map((p) => p[0])
			.join('')
			.slice(0, 2)
	);
	let roleLabel = $derived(
		user.role === 'AIMO_STAFF'
			? 'Valio Aimo staff, read-only'
			: user.role === 'APPROVER'
				? 'Approver'
				: 'Buyer admin'
	);
	let liveAreas = $derived(
		(Object.entries(modes) as [Area, 'mock' | 'http'][])
			.filter(([a, m]) => m === 'http' && a !== 'auth')
			.map(([a]) => a)
	);
</script>

{#snippet navGroup(label: string, items: Item[])}
	<Sidebar.Group>
		<Sidebar.GroupLabel>{label}</Sidebar.GroupLabel>
		<Sidebar.GroupContent>
			<Sidebar.Menu>
				{#each items as item (item.href)}
					<Sidebar.MenuItem>
						<Sidebar.MenuButton isActive={isActive(item.href)} tooltipContent={item.label}>
							{#snippet child({ props })}
								<a
									href={resolve(`${item.href}`)}
									aria-current={isActive(item.href) ? 'page' : undefined}
									{...props}
								>
									<item.icon />
									<span>{item.label}</span>
								</a>
							{/snippet}
						</Sidebar.MenuButton>
						{#if item.count}
							<Sidebar.MenuBadge
								class="bg-hold/15 text-hold peer-data-active/menu-button:text-hold"
								aria-label="{item.count} waiting">{item.count}</Sidebar.MenuBadge
							>
						{/if}
					</Sidebar.MenuItem>
				{/each}
			</Sidebar.Menu>
		</Sidebar.GroupContent>
	</Sidebar.Group>
{/snippet}

<Sidebar.Root collapsible="icon" variant="inset">
	<Sidebar.Header>
		<Sidebar.Menu>
			<Sidebar.MenuItem>
				<Sidebar.MenuButton size="lg">
					{#snippet child({ props })}
						<a href={resolve('/(marketing)')} {...props}>
							<Roundel size={32} />
							<span class="grid leading-tight">
								<span class="font-display text-[1.1875rem] font-medium tracking-tight"
									>Saint Elmo</span
								>
								<span class="truncate text-xs text-muted-foreground">
									{user.organisation?.name ?? 'Valio Aimo operations'}
								</span>
							</span>
						</a>
					{/snippet}
				</Sidebar.MenuButton>
			</Sidebar.MenuItem>
		</Sidebar.Menu>
	</Sidebar.Header>

	<Sidebar.Content>
		{@render navGroup(isStaff ? 'Watch' : 'Decide', work)}
		{@render navGroup('Look up', reference)}
	</Sidebar.Content>

	<Sidebar.Footer>
		<div
			class="mx-2 mb-1 rounded-lg border border-sidebar-border bg-background/60 px-3 py-2.5 text-xs group-data-[collapsible=icon]:hidden"
		>
			<p class="font-medium text-foreground">
				{liveAreas.length ? 'Connected to the backend' : 'Demo mode'}
			</p>
			<p class="mt-0.5 text-muted-foreground">
				{liveAreas.length
					? `Live: sign-in, ${liveAreas.join(', ')}. The rest is demo data until its API lands.`
					: 'Everything here is built-in demo data.'}
			</p>
		</div>
		<Sidebar.Menu>
			<Sidebar.MenuItem>
				<DropdownMenu.Root>
					<DropdownMenu.Trigger>
						{#snippet child({ props })}
							<Sidebar.MenuButton size="lg" class="data-[state=open]:bg-sidebar-accent" {...props}>
								<Avatar.Root class="size-8 rounded-lg">
									<Avatar.Fallback
										class="rounded-lg bg-primary/10 text-xs font-semibold text-primary"
										>{initials}</Avatar.Fallback
									>
								</Avatar.Root>
								<span class="grid flex-1 text-left leading-tight">
									<span class="truncate text-sm font-medium">{user.name}</span>
									<span class="truncate text-xs text-muted-foreground">{roleLabel}</span>
								</span>
								<ChevronsUpDownIcon class="ml-auto size-4" />
							</Sidebar.MenuButton>
						{/snippet}
					</DropdownMenu.Trigger>
					<DropdownMenu.Content
						side="top"
						align="start"
						class="w-(--bits-dropdown-menu-anchor-width) min-w-56"
					>
						<DropdownMenu.Label class="font-normal">
							<p class="text-sm font-medium text-foreground">{user.name}</p>
							<p class="text-xs text-muted-foreground">{user.email}</p>
						</DropdownMenu.Label>
						<DropdownMenu.Separator />
						<form method="POST" action="/logout">
							<DropdownMenu.Item>
								{#snippet child({ props })}
									<button type="submit" {...props} class="{props.class} w-full">
										<LogOutIcon /> Sign out
									</button>
								{/snippet}
							</DropdownMenu.Item>
						</form>
					</DropdownMenu.Content>
				</DropdownMenu.Root>
			</Sidebar.MenuItem>
		</Sidebar.Menu>
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
