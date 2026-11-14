<script lang="ts">
	import { resolve } from '$app/paths';
	import CircleCheckBigIcon from '@lucide/svelte/icons/circle-check-big';
	import ListChecksIcon from '@lucide/svelte/icons/list-checks';
	import { Button } from '#lib/components/ui/button/index.js';
	import * as Empty from '#lib/components/ui/empty/index.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<Empty.Root class="min-h-96 rounded-xl border border-dashed bg-card/50">
	<Empty.Header>
		<Empty.Media variant="icon">
			{#if data.pending.length}<ListChecksIcon />{:else}<CircleCheckBigIcon />{/if}
		</Empty.Media>
		{#if data.pending.length}
			<Empty.Title>Choose an order to review</Empty.Title>
			<Empty.Description>
				You’ll see the policy’s reasons next to the agent’s note, every line’s unit conversion, and
				the live price and stock it was checked against.
			</Empty.Description>
		{:else}
			<Empty.Title>You’re all caught up</Empty.Title>
			<Empty.Description
				>To change what agents may decide alone, edit their mandates.</Empty.Description
			>
		{/if}
	</Empty.Header>
	<Empty.Content>
		{#if data.pending.length}
			<Button href={resolve(`inbox/${data.pending.at(-1)?.orderId}`)}
				>Review the oldest first</Button
			>
		{:else}
			<Button variant="outline" href={resolve('agents')}>Open agents & mandates</Button>
		{/if}
	</Empty.Content>
</Empty.Root>
