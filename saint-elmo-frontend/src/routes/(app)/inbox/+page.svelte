<script lang="ts">
	import { resolve } from '$app/paths';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<div
	class="grid h-full min-h-80 place-items-center rounded-md border border-dashed border-line-strong px-6 py-12 text-center"
>
	<div class="max-w-[38ch]">
		{#if data.pending.length}
			<p class="font-semibold text-ink">Choose an order to review</p>
			<p class="mt-1 text-sm text-muted">
				You’ll see the policy’s reasons next to the agent’s note, every line’s unit conversion, and
				the live price and stock it was checked against.
			</p>
			<a href={resolve(`inbox/${data.pending.at(-1)?.orderId}`)} class="btn btn-primary mt-5">
				Review the oldest first
			</a>
		{:else}
			<p class="font-semibold text-ink">You’re all caught up</p>
			<p class="mt-1 text-sm text-muted">
				To change what agents may decide alone, edit their mandates.
			</p>
			<a href={resolve('agents')} class="btn mt-5">Open agents and mandates</a>
		{/if}
	</div>
</div>
