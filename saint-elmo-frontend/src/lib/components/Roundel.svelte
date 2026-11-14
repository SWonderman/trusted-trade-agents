<script lang="ts">
	/** The logo: Saint Erasmus (Saint Elmo) from Grünewald's panel, in a gilt ring. */
	let { size = 36, ring = 'gold' }: { size?: number; ring?: 'gold' | 'line' } = $props();
	let src = $derived(size > 96 ? '/art/erasmus-roundel-512.webp' : '/art/erasmus-roundel-192.webp');
</script>

<span class="roundel" class:line={ring === 'line'} style:--size="{size}px">
	<img {src} alt="" width={size} height={size} decoding="async" />
</span>

<style>
	.roundel {
		display: inline-block;
		flex-shrink: 0;
		width: var(--size);
		height: var(--size);
		border-radius: 50%;
		padding: max(2px, calc(var(--size) * 0.045));
		background: conic-gradient(from 210deg, #8a6a24, #e6c873, #b38a33, #f1dc98, #8a6a24);
	}
	.roundel.line {
		background: var(--se-line-strong);
		padding: 1px;
	}
	img {
		display: block;
		width: 100%;
		height: 100%;
		border-radius: 50%;
		object-fit: cover;
	}
</style>
