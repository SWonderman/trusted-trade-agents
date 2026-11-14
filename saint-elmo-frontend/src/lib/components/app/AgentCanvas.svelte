<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { prefersReducedMotion } from 'svelte/motion';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import Roundel from '#lib/components/Roundel.svelte';
	import type { AgentSummary } from '#lib/api/types.js';
	import { moneyWhole, relative } from '#lib/format.js';

	/**
	 * The organisation's agents as nodes, each wired to Saint Elmo, which alone talks to
	 * Valio Aimo: the same picture as the landing page, with live state on every node.
	 * Wires are measured from the real card positions, so they follow any layout.
	 */

	let { agents, waiting }: { agents: AgentSummary[]; waiting: Record<string, number> } = $props();

	let canvas = $state<HTMLElement>();
	let wires = $state<{ id: string; d: string; live: boolean; off: boolean }[]>([]);
	let trunk = $state('');
	let size = $state({ w: 0, h: 0 });

	const HOUR = 3_600_000;
	const recentlyActive = (a: AgentSummary) =>
		a.status === 'ACTIVE' &&
		!!a.lastActiveAt &&
		Date.now() - new Date(a.lastActiveAt).getTime() < 6 * HOUR;

	function measure() {
		if (!canvas) return;
		const box = canvas.getBoundingClientRect();
		size = { w: box.width, h: box.height };
		const hub = canvas.querySelector<HTMLElement>('[data-hub-mark]')?.getBoundingClientRect();
		const aimo = canvas.querySelector<HTMLElement>('[data-aimo]')?.getBoundingClientRect();
		if (!hub || !aimo) return;
		const hx = hub.left - box.left;
		const hy = hub.top - box.top + hub.height / 2;
		const tx = hub.right - box.left;
		const ax = aimo.left - box.left;
		const ay = aimo.top - box.top + aimo.height / 2;
		const tm = (tx + ax) / 2;
		trunk = `M ${tx} ${hy} C ${tm} ${hy}, ${tm} ${ay}, ${ax} ${ay}`;
		wires = agents.flatMap((a) => {
			const el = canvas!.querySelector<HTMLElement>(`[data-agent="${a.id}"]`);
			if (!el) return [];
			const r = el.getBoundingClientRect();
			const x = r.right - box.left;
			const y = r.top - box.top + r.height / 2;
			const mid = (x + hx) / 2;
			return [
				{
					id: a.id,
					d: `M ${x} ${y} C ${mid} ${y}, ${mid} ${hy}, ${hx} ${hy}`,
					live: recentlyActive(a),
					off: a.status !== 'ACTIVE'
				}
			];
		});
	}

	// Re-measure when the canvas resizes or the agents change.
	function observe(node: HTMLElement) {
		const ro = new ResizeObserver(measure);
		ro.observe(node);
		return () => ro.disconnect();
	}
	$effect(() => {
		void agents;
		measure();
	});

	let motion = $derived(!prefersReducedMotion.current);
</script>

<div class="canvas" bind:this={canvas} {@attach observe}>
	<svg class="wires" width={size.w} height={size.h} aria-hidden="true">
		{#if trunk}<path class="wire trunk" d={trunk} />{/if}
		{#each wires as w (w.id)}
			<path id="wire-{w.id}" class={['wire', w.off && 'off', w.live && 'live']} d={w.d} />
			{#if w.live && motion}
				<!-- A call travelling from the agent to Saint Elmo -->
				<circle r="3.5" class="pulse">
					<animateMotion dur="2.6s" repeatCount="indefinite" rotate="auto">
						<mpath href="#wire-{w.id}" />
					</animateMotion>
				</circle>
			{/if}
		{/each}
	</svg>

	<div class="agents">
		{#each agents as a (a.id)}
			{@const m = a.mandate}
			{@const used = Math.min(100, (a.periodSpend.committed / m.periodSpendCap) * 100)}
			{@const n = waiting[a.id] ?? 0}
			<a
				href={resolve(`agents/${a.id}`)}
				data-agent={a.id}
				data-sveltekit-noscroll
				aria-current={page.params.agentId === a.id ? 'page' : undefined}
				class={['node', a.status !== 'ACTIVE' && 'disabled']}
			>
				<div class="node-head">
					<span
						class={['status', a.status === 'ACTIVE' ? 'on' : 'off']}
						title={a.status === 'ACTIVE' ? 'Active' : 'Disabled'}
						aria-hidden="true"
					></span>
					<span class="name code">{a.name}</span>
					{#if n}
						<span class="waiting" title="Orders waiting for a person">{n} waiting</span>
					{/if}
				</div>
				<p class="purpose">{a.purpose}</p>
				<div class="spend">
					<div
						class="bar"
						role="meter"
						aria-valuenow={Math.round(used)}
						aria-valuemin={0}
						aria-valuemax={100}
						aria-label="Spend this period"
					>
						<span style:width="{used}%" class={[used > 85 && 'high']}></span>
					</div>
					<span class="tabular"
						>{moneyWhole(a.periodSpend.committed)}
						<span class="soft"
							>/ {moneyWhole(m.periodSpendCap)} {m.spendPeriod === 'WEEK' ? 'wk' : 'mo'}</span
						></span
					>
				</div>
				<div class="node-foot">
					<span class="tabular">alone ≤ {moneyWhole(m.autoApproveUpTo)}</span>
					<span class="tokens"><KeyRoundIcon aria-hidden="true" />{a.activeKeys}</span>
					<span class="seen"
						>{a.status !== 'ACTIVE'
							? 'Disabled'
							: a.lastActiveAt
								? relative(a.lastActiveAt)
								: 'Never used'}</span
					>
				</div>
			</a>
		{/each}
		<a href={resolve('agents/new')} data-sveltekit-noscroll class="node ghost">
			<PlusIcon aria-hidden="true" /> New agent
		</a>
	</div>

	<div class="hub" data-hub>
		<span class="hub-mark" data-hub-mark><Roundel size={72} /></span>
		<p class="hub-name">Saint Elmo</p>
		<p class="hub-note">checks every call against its agent’s mandate</p>
	</div>

	<div class="aimo" data-aimo>
		<img src="/brand/valio-aimo-wordmark.png" alt="Valio Aimo" width="340" height="140" />
	</div>
</div>

<style>
	.canvas {
		position: relative;
		display: grid;
		grid-template-columns: minmax(16rem, 22rem) 1fr auto;
		align-items: center;
		gap: 2rem;
		padding: 2rem;
		border-radius: 1rem;
		background:
			radial-gradient(ellipse 40% 60% at 62% 50%, oklch(0.9 0.07 82 / 0.3), transparent 70%),
			linear-gradient(oklch(0.24 0.03 60 / 0.035) 1px, transparent 1px) 0 0 / 100% 1.75rem,
			linear-gradient(90deg, oklch(0.24 0.03 60 / 0.035) 1px, transparent 1px) 0 0 / 1.75rem 100%,
			var(--card);
		box-shadow: inset 0 0 0 1px var(--border);
		min-height: 24rem;
	}

	.wires {
		position: absolute;
		inset: 0;
		pointer-events: none;
		overflow: visible;
	}
	.wire {
		fill: none;
		stroke: oklch(0.84 0.085 86);
		stroke-width: 2;
	}
	.wire.trunk {
		stroke-width: 2.5;
	}
	.wire.off {
		stroke: oklch(0.6 0.02 85 / 0.35);
		stroke-dasharray: 4 5;
	}
	.pulse {
		fill: oklch(0.72 0.12 78);
	}

	.agents {
		position: relative;
		display: grid;
		gap: 0.875rem;
	}
	.node {
		position: relative;
		display: grid;
		gap: 0.5rem;
		padding: 0.875rem 1rem;
		border-radius: 0.875rem;
		background: var(--card);
		box-shadow:
			0 0 0 1px var(--border),
			0 12px 24px -18px oklch(0.3 0.05 60 / 0.35);
		transition:
			box-shadow 200ms,
			transform 200ms;
	}
	.node:hover {
		transform: translateY(-1px);
		box-shadow:
			0 0 0 1px oklch(0.84 0.085 86),
			0 16px 30px -18px oklch(0.3 0.05 60 / 0.45);
	}
	.node[aria-current='page'] {
		box-shadow:
			0 0 0 2px oklch(0.84 0.085 86),
			0 0 0 6px oklch(0.84 0.085 86 / 0.2);
	}
	.node:focus-visible {
		outline: 2px solid var(--ring);
		outline-offset: 3px;
	}
	.node.disabled {
		opacity: 0.6;
	}
	.node-head {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}
	.status {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
	}
	.status.on {
		background: var(--ok);
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--ok) 18%, transparent);
	}
	.status.off {
		background: var(--muted-foreground);
	}
	.name {
		font-weight: 600;
	}
	.waiting {
		margin-left: auto;
		padding: 0.05rem 0.5rem;
		border-radius: 999px;
		background: color-mix(in oklch, var(--hold) 15%, transparent);
		color: var(--hold);
		font-size: 0.6875rem;
		font-weight: 600;
	}
	.purpose {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 0.8125rem;
		color: var(--muted-foreground);
	}
	.spend {
		display: flex;
		align-items: center;
		gap: 0.625rem;
		font-size: 0.75rem;
	}
	.bar {
		flex: 1;
		height: 0.3rem;
		border-radius: 999px;
		background: var(--muted);
		overflow: hidden;
	}
	.bar span {
		display: block;
		height: 100%;
		border-radius: inherit;
		background: var(--primary);
	}
	.bar span.high {
		background: var(--hold);
	}
	.soft {
		color: var(--muted-foreground);
	}
	.node-foot {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		font-size: 0.6875rem;
		color: var(--muted-foreground);
	}
	.tokens {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
	}
	.tokens :global(svg) {
		width: 0.75rem;
		height: 0.75rem;
	}
	.seen {
		margin-left: auto;
	}
	.ghost {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.375rem;
		padding-block: 0.75rem;
		background: transparent;
		box-shadow: none;
		border: 1.5px dashed var(--input);
		font-size: 0.8125rem;
		color: var(--muted-foreground);
	}
	.ghost:hover {
		border-color: oklch(0.84 0.085 86);
		color: var(--foreground);
		box-shadow: none;
	}
	.ghost :global(svg) {
		width: 1rem;
		height: 1rem;
	}

	.hub {
		position: relative;
		justify-self: center;
		display: grid;
		justify-items: center;
		text-align: center;
	}
	.hub-mark {
		display: inline-flex;
		border-radius: 50%;
	}
	.hub :global(.roundel) {
		box-shadow:
			0 0 0 8px var(--card),
			0 0 0 9px oklch(0.84 0.085 86 / 0.6),
			0 18px 40px -14px oklch(0.35 0.06 60 / 0.45);
		border-radius: 50%;
	}
	.hub-name {
		margin-top: 0.875rem;
		font-family: var(--font-display);
		font-size: 1.125rem;
		font-weight: 500;
	}
	.hub-note {
		max-width: 12rem;
		font-size: 0.75rem;
		color: var(--muted-foreground);
	}
	.aimo {
		position: relative;
		padding: 0.75rem 1rem;
		border-radius: 0.875rem;
		background: var(--card);
		box-shadow:
			0 0 0 1px var(--border),
			0 12px 24px -18px oklch(0.3 0.05 60 / 0.35);
	}
	.aimo img {
		height: 2.25rem;
		width: auto;
		border-radius: 4px;
	}

	/* Narrow: a single column, agents first; the wiring is implied by the order. */
	@media (max-width: 860px) {
		.canvas {
			grid-template-columns: 1fr;
			justify-items: stretch;
			padding: 1.25rem;
		}
		.wires {
			display: none;
		}
		.hub,
		.aimo {
			justify-self: center;
		}
	}
</style>
