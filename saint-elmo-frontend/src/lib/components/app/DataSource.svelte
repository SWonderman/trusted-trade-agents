<script lang="ts">
	import * as Tooltip from '#lib/components/ui/tooltip/index.js';

	let { mode }: { mode: 'mock' | 'http' } = $props();
</script>

<!-- Says plainly whether a page shows the real backend or demo data, so nobody mistakes one for the other. -->
<Tooltip.Root>
	<Tooltip.Trigger>
		{#snippet child({ props })}
			<button
				{...props}
				type="button"
				class={[
					'inline-flex h-5.5 items-center gap-1.5 rounded-full px-2 text-[0.6875rem] font-medium tracking-wide uppercase ring-1 ring-inset',
					mode === 'http'
						? 'bg-ok/8 text-ok ring-ok/20'
						: 'bg-gold/12 text-gold-deep ring-gold/30 dark:text-gold'
				]}
			>
				<span
					class={['size-1.5 rounded-full', mode === 'http' ? 'bg-ok' : 'bg-gold-deep dark:bg-gold']}
					aria-hidden="true"
				></span>
				{mode === 'http' ? 'Live' : 'Demo data'}
			</button>
		{/snippet}
	</Tooltip.Trigger>
	<Tooltip.Content class="max-w-64">
		{mode === 'http'
			? 'From the Saint Elmo backend.'
			: 'From built-in demo data: the backend doesn’t serve this area yet. Changes last until the server restarts.'}
	</Tooltip.Content>
</Tooltip.Root>
