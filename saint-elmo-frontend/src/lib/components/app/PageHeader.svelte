<script lang="ts">
	import type { Snippet } from 'svelte';
	import DataSource from './DataSource.svelte';

	let {
		title,
		description,
		source,
		actions
	}: {
		title: string;
		description?: string;
		/** Where this page's data comes from, shown next to the title. */
		source?: 'mock' | 'http';
		actions?: Snippet;
	} = $props();
</script>

<header class="mb-8 flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
	<div class="min-w-0">
		<div class="flex flex-wrap items-center gap-3">
			<h1 class="font-display-tight text-[2.125rem] text-foreground">{title}</h1>
			{#if source}<DataSource mode={source} />{/if}
		</div>
		{#if description}
			<p class="mt-2 max-w-[68ch] text-sm text-pretty text-muted-foreground">{description}</p>
		{/if}
	</div>
	{#if actions}
		<div class="flex flex-wrap items-center gap-2">{@render actions()}</div>
	{/if}
</header>
