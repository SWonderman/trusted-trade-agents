<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import ChevronsUpDownIcon from '@lucide/svelte/icons/chevrons-up-down';
	import XIcon from '@lucide/svelte/icons/x';
	import * as Command from '#lib/components/ui/command/index.js';
	import * as Popover from '#lib/components/ui/popover/index.js';
	import { cn } from '#lib/utils.js';

	/**
	 * Pick category codes from the ones products actually use, by search. The source
	 * data has no category names, so each code shows its product count, and codes are
	 * grouped by their first three digits, which related categories share.
	 * Posts as one comma-separated field, the same as the old free-text input.
	 */

	let {
		id,
		name,
		categories,
		value = ''
	}: {
		id: string;
		name: string;
		categories: { code: string; productCount: number }[];
		/** Initial codes, comma- or space-separated (e.g. after a failed submit). */
		value?: string;
	} = $props();

	let open = $state(false);
	// Seeded once from the initial value; from then on the picker owns the selection.
	let selected = $state<string[]>(
		// svelte-ignore state_referenced_locally
		value.split(/[\s,]+/).filter(Boolean)
	);

	const count = new Intl.NumberFormat('en-GB');
	let byCode = $derived(new Map(categories.map((c) => [c.code, c.productCount])));
	let groups = $derived.by(() => {
		const m: Record<string, { code: string; productCount: number }[]> = {};
		for (const c of categories.toSorted((a, b) => a.code.localeCompare(b.code))) {
			(m[c.code.slice(0, 3)] ??= []).push(c);
		}
		return Object.entries(m).map(([prefix, items]) => ({
			prefix,
			items,
			total: items.reduce((n, c) => n + c.productCount, 0)
		}));
	});
	let products = $derived(selected.reduce((n, c) => n + (byCode.get(c) ?? 0), 0));

	function toggle(code: string) {
		selected = selected.includes(code) ? selected.filter((c) => c !== code) : [...selected, code];
	}
	function toggleGroup(codes: string[]) {
		const all = codes.every((c) => selected.includes(c));
		selected = all
			? selected.filter((c) => !codes.includes(c))
			: [...new Set([...selected, ...codes])];
	}
</script>

<input type="hidden" {name} value={selected.join(',')} />

<Popover.Root bind:open>
	<Popover.Trigger
		{id}
		class={cn(
			'flex h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-transparent px-3 text-left text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50',
			!selected.length && 'text-muted-foreground'
		)}
		aria-label="Choose categories"
	>
		{#if selected.length}
			<span>
				{selected.length}
				{selected.length === 1 ? 'category' : 'categories'}
				<span class="text-muted-foreground">· {count.format(products)} products</span>
			</span>
		{:else}
			Any category
		{/if}
		<ChevronsUpDownIcon class="size-4 shrink-0 opacity-60" aria-hidden="true" />
	</Popover.Trigger>
	<Popover.Content class="w-(--bits-popover-anchor-width) min-w-72 p-0" align="start">
		<Command.Root>
			<Command.Input placeholder="Search codes, e.g. 104" />
			<Command.List class="max-h-72">
				<Command.Empty>No category code matches.</Command.Empty>
				{#each groups as g (g.prefix)}
					{@const codes = g.items.map((c) => c.code)}
					{@const all = codes.every((c) => selected.includes(c))}
					<Command.Group heading="{g.prefix}·· · {count.format(g.total)} products">
						{#if g.items.length > 1}
							<Command.Item
								value="{g.prefix} all"
								keywords={codes}
								onSelect={() => toggleGroup(codes)}
								class="text-muted-foreground"
							>
								<CheckIcon class={cn('size-4', !all && 'opacity-0')} aria-hidden="true" />
								All {g.items.length} in {g.prefix}··
							</Command.Item>
						{/if}
						{#each g.items as c (c.code)}
							<Command.Item value={c.code} onSelect={() => toggle(c.code)}>
								<CheckIcon
									class={cn('size-4', !selected.includes(c.code) && 'opacity-0')}
									aria-hidden="true"
								/>
								<span class="flex-1 code">{c.code}</span>
								<span class="text-xs text-muted-foreground tabular"
									>{count.format(c.productCount)}</span
								>
							</Command.Item>
						{/each}
					</Command.Group>
				{/each}
			</Command.List>
			<div class="flex items-center justify-between gap-2 border-t px-2 py-1.5">
				<button
					type="button"
					class="rounded px-2 py-1 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40"
					disabled={!selected.length}
					onclick={() => (selected = [])}>Clear</button
				>
				<button
					type="button"
					class="rounded bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground"
					onclick={() => (open = false)}>Done</button
				>
			</div>
		</Command.Root>
	</Popover.Content>
</Popover.Root>

{#if selected.length}
	<ul class="mt-2 flex flex-wrap gap-1" aria-label="Chosen categories">
		{#each selected.toSorted() as code (code)}
			<li
				class="inline-flex items-center gap-1 rounded-md bg-muted py-0.5 pr-1 pl-1.5 code text-xs"
			>
				{code}
				<button
					type="button"
					class="rounded p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground"
					aria-label="Remove {code}"
					onclick={() => toggle(code)}
				>
					<XIcon class="size-3" aria-hidden="true" />
				</button>
			</li>
		{/each}
	</ul>
{/if}
