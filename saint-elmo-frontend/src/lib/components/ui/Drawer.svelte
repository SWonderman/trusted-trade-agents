<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	let {
		title,
		description,
		onclose,
		children,
		footer,
		width = '34rem'
	}: {
		title: string;
		description?: string;
		onclose: () => void;
		children: Snippet;
		footer?: Snippet;
		width?: string;
	} = $props();

	/** A native modal dialog gives focus trapping, Esc and inert background for free. */
	function open(dialog: HTMLDialogElement) {
		dialog.showModal();
		return () => dialog.close();
	}
</script>

<dialog
	{@attach open}
	class="drawer"
	style:--drawer-width={width}
	aria-labelledby="drawer-title"
	{onclose}
	onclick={(e) => {
		if (e.target === e.currentTarget) onclose();
	}}
>
	<div class="flex h-full flex-col">
		<header class="flex items-start justify-between gap-4 border-b border-line px-6 py-5">
			<div>
				<h2 id="drawer-title" class="text-lg font-semibold text-ink">{title}</h2>
				{#if description}<p class="mt-1 text-sm text-muted">{description}</p>{/if}
			</div>
			<button class="btn btn-quiet btn-sm -mr-2" onclick={onclose} aria-label="Close">
				<Icon name="x" />
			</button>
		</header>
		<div class="flex-1 overflow-y-auto px-6 py-5">
			{@render children()}
		</div>
		{#if footer}
			<footer class="flex justify-end gap-2 border-t border-line bg-surface px-6 py-4">
				{@render footer()}
			</footer>
		{/if}
	</div>
</dialog>

<style>
	.drawer {
		position: fixed;
		inset: 0 0 0 auto;
		margin: 0;
		width: min(var(--drawer-width), 100vw);
		max-width: 100vw;
		height: 100dvh;
		max-height: 100dvh;
		padding: 0;
		border: 0;
		border-left: 1px solid var(--se-line);
		border-radius: var(--radius-lg) 0 0 var(--radius-lg);
		background: var(--se-panel);
		color: var(--se-ink);
		box-shadow: -24px 0 48px -24px rgb(16 24 48 / 0.28);
		animation: slide-in 180ms ease-out;
	}
	.drawer::backdrop {
		background: rgb(16 20 32 / 0.36);
	}
	@keyframes slide-in {
		from {
			transform: translateX(24px);
			opacity: 0;
		}
	}
</style>
