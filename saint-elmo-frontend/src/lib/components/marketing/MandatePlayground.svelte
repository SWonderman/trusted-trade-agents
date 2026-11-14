<script lang="ts">
	import { crossfade, fade } from 'svelte/transition';
	import { flip } from 'svelte/animate';
	import { cubicOut } from 'svelte/easing';
	import { prefersReducedMotion } from 'svelte/motion';
	import { untrack } from 'svelte';

	/**
	 * A mandate you can edit, and the policy judging eight orders against it live.
	 * The rules below are a small, deterministic stand-in for Saint Elmo's policy:
	 * same mandate, same orders, same verdicts, every time.
	 */

	type Outcome = 'AUTO_APPROVE' | 'NEEDS_HUMAN' | 'REJECT';
	type Substitutes = 'NEVER' | 'IF_REQUIREMENTS_HOLD' | 'ALWAYS_ASK';

	interface Order {
		id: string;
		name: string;
		total: number;
		note?: string;
		lactoseFree: boolean;
		substitute?: boolean;
		late?: boolean;
		peanuts?: boolean;
	}

	const orders: Order[] = [
		{ id: 'milk', name: 'Lactose-free milk', note: '50 cases', total: 1840, lactoseFree: true },
		{ id: 'butter', name: 'Butter spread', note: '20 cases', total: 420, lactoseFree: true },
		{ id: 'cream', name: 'Whipping cream', note: '24 litres', total: 310, lactoseFree: true },
		{ id: 'arki', name: 'Regular milk', note: 'not lactose-free', total: 238, lactoseFree: false },
		{
			id: 'oat',
			name: 'Oat drink',
			note: 'substitute, +6% per litre',
			total: 520,
			lactoseFree: true,
			substitute: true
		},
		{
			id: 'yoghurt',
			name: 'Yoghurt',
			note: 'arrives a day late',
			total: 640,
			lactoseFree: true,
			late: true
		},
		{
			id: 'cookies',
			name: 'Lobby cookies',
			note: 'contain peanuts',
			total: 96,
			lactoseFree: true,
			peanuts: true
		},
		{ id: 'banquet', name: 'Banquet cheese', note: '40 cases', total: 2350, lactoseFree: true }
	];

	// The mandate, as the backend's demo seed sets it for dairy-restock
	let autoUpTo = $state(1500);
	let limit = $state(2000);
	let lactoseFree = $state(true);
	let noPeanuts = $state(true);
	let lateAsks = $state(true);
	let substitutes = $state<Substitutes>('IF_REQUIREMENTS_HOLD');

	const rank: Record<Outcome, number> = { AUTO_APPROVE: 0, NEEDS_HUMAN: 1, REJECT: 2 };

	function judge(o: Order): { outcome: Outcome; code: string } {
		const reasons: [Outcome, string][] = [];
		if (o.total > limit) reasons.push(['REJECT', 'OVER_ORDER_LIMIT']);
		if (noPeanuts && o.peanuts) reasons.push(['REJECT', 'CONTAINS_EXCLUDED_ALLERGEN']);
		if (o.substitute && substitutes === 'NEVER')
			reasons.push(['REJECT', 'SUBSTITUTES_NOT_ALLOWED']);
		if (lactoseFree && !o.lactoseFree) reasons.push(['NEEDS_HUMAN', 'MISSING_REQUIRED_CLAIM']);
		if (o.total > autoUpTo) reasons.push(['NEEDS_HUMAN', 'OVER_AUTO_APPROVE_LIMIT']);
		if (o.substitute && substitutes === 'ALWAYS_ASK')
			reasons.push(['NEEDS_HUMAN', 'SUBSTITUTE_NEEDS_APPROVAL']);
		if (o.late && lateAsks) reasons.push(['NEEDS_HUMAN', 'LATE_DELIVERY']);
		if (!reasons.length) return { outcome: 'AUTO_APPROVE', code: 'WITHIN_MANDATE' };
		const worst = reasons.reduce((a, b) => (rank[b[0]] > rank[a[0]] ? b : a));
		return { outcome: worst[0], code: worst[1] };
	}

	let judged = $derived(orders.map((o) => ({ ...o, ...judge(o) })));
	const lanes = [
		{ outcome: 'AUTO_APPROVE', title: 'Decides alone', tone: 'ok' },
		{ outcome: 'NEEDS_HUMAN', title: 'Waits for a person', tone: 'hold' },
		{ outcome: 'REJECT', title: 'Never ordered', tone: 'stop' }
	] as const;
	let byLane = $derived(
		Object.fromEntries(
			lanes.map((l) => [l.outcome, judged.filter((o) => o.outcome === l.outcome)])
		) as Record<Outcome, typeof judged>
	);

	const eur = new Intl.NumberFormat('en-IE', {
		style: 'currency',
		currency: 'EUR',
		maximumFractionDigits: 0
	});

	// Set by the visitor's first change, so only orders that move afterwards glow.
	let touched = $state(false);
	let reduced = $derived(prefersReducedMotion.current);
	let d = $derived(reduced ? 0 : 1);

	const [send, receive] = crossfade({
		duration: 550,
		easing: cubicOut,
		fallback: (node) => fade(node, { duration: 220 })
	});
	// Orders glide to their new lane; with reduced motion they fade out and in, in place.
	function leave(node: Element, params: { key: string }) {
		return reduced ? fade(node, { duration: 220 }) : send(node, params);
	}
	function arrive(node: Element, params: { key: string }) {
		return reduced ? fade(node, { delay: 140, duration: 320 }) : receive(node, params);
	}
	// A soft gold glow on every order that lands in a lane after a change. No movement.
	function arrived(node: HTMLElement) {
		return flashOnMount(node, 'arrived', 2000);
	}
	// A value in the charter flashes gold when the visitor changes it (not on page load).
	function changed(node: HTMLElement) {
		return flashOnMount(node, 'flash', 1000);
	}
	// A lane count bumps when its number changes: the {#key} re-creates only that badge.
	function bumped(node: HTMLElement) {
		return flashOnMount(node, 'bump', 700);
	}
	function flashOnMount(node: HTMLElement, cls: string, ms: number) {
		if (!untrack(() => touched)) return;
		node.classList.add(cls);
		const id = setTimeout(() => node.classList.remove(cls), ms);
		return () => clearTimeout(id);
	}

	const substituteLabel: Record<Substitutes, string> = {
		NEVER: 'never allowed',
		IF_REQUIREMENTS_HOLD: 'allowed when every requirement still holds',
		ALWAYS_ASK: 'always shown to a person'
	};
</script>

{#snippet value(text: string)}
	{#key text}
		<mark class="val" {@attach changed}>{text}</mark>
	{/key}
{/snippet}

<!-- Its feedback is colour and glow, not travel, so it may run for reduced-motion visitors too. -->
<div class="playground" data-motion="allowed">
	<!-- The mandate, written out like a charter -->
	<div class="charter">
		<p class="charter-head">
			<span class="seal">Mandate</span>
			<span class="code">dairy-restock</span>
			<span class="charter-note">Set by a buyer admin. The agent can read it, never change it.</span
			>
		</p>

		<p class="writ">
			It may order up to {@render value(eur.format(autoUpTo))} on its own, and never more than
			{@render value(eur.format(limit))} at once. Everything it buys
			{@render value(lactoseFree ? 'must be lactose-free' : 'can be any dairy product')},
			{@render value(noPeanuts ? 'nothing may contain peanuts' : 'peanuts are allowed')},
			substitutes are
			{@render value(substituteLabel[substitutes])}, and a late delivery
			{@render value(lateAsks ? 'waits for a person' : 'is accepted')}.
		</p>

		<div class="controls" role="group" aria-label="Try changing the mandate">
			<label class="slider">
				<span class="slider-label">
					Decides alone up to <output class="tabular">{eur.format(autoUpTo)}</output>
				</span>
				<input
					type="range"
					min="0"
					max="2500"
					step="50"
					bind:value={autoUpTo}
					oninput={() => {
						touched = true;
						if (autoUpTo > limit) limit = autoUpTo;
					}}
				/>
			</label>
			<label class="slider">
				<span class="slider-label">
					Order limit <output class="tabular">{eur.format(limit)}</output>
				</span>
				<input
					type="range"
					min="500"
					max="3000"
					step="50"
					bind:value={limit}
					oninput={() => {
						touched = true;
						if (autoUpTo > limit) autoUpTo = limit;
					}}
				/>
			</label>

			<div class="toggles">
				<button
					type="button"
					aria-pressed={lactoseFree}
					onclick={() => {
						touched = true;
						lactoseFree = !lactoseFree;
					}}
				>
					Lactose-free required
				</button>
				<button
					type="button"
					aria-pressed={noPeanuts}
					onclick={() => {
						touched = true;
						noPeanuts = !noPeanuts;
					}}
				>
					No peanuts
				</button>
				<button
					type="button"
					aria-pressed={lateAsks}
					onclick={() => {
						touched = true;
						lateAsks = !lateAsks;
					}}
				>
					Late delivery asks
				</button>
			</div>

			<div class="segmented" role="radiogroup" aria-label="Substitutes">
				<span class="segmented-label" aria-hidden="true">Substitutes</span>
				{#each [['NEVER', 'Never'], ['IF_REQUIREMENTS_HOLD', 'If requirements hold'], ['ALWAYS_ASK', 'Always ask']] as const as [v, label] (v)}
					<button
						type="button"
						role="radio"
						aria-checked={substitutes === v}
						onclick={() => {
							touched = true;
							substitutes = v;
						}}
					>
						{label}
					</button>
				{/each}
			</div>
		</div>
	</div>

	<!-- The policy's verdicts, live -->
	<div class="lanes">
		{#each lanes as lane (lane.outcome)}
			<section class="lane lane-{lane.tone}" aria-label={lane.title}>
				<header>
					<span class="dot" aria-hidden="true"></span>
					<span class="lane-title">{lane.title}</span>
					{#key byLane[lane.outcome].length}
						<span class="lane-count tabular" {@attach bumped}>{byLane[lane.outcome].length}</span>
					{/key}
				</header>
				<p class="lane-code code">{lane.outcome}</p>
				<ul>
					{#each byLane[lane.outcome] as o (o.id)}
						<li
							in:arrive={{ key: o.id }}
							out:leave={{ key: o.id }}
							animate:flip={{ duration: 550 * d, easing: cubicOut }}
							{@attach arrived}
						>
							<div class="order-top">
								<span class="order-name">{o.name}</span>
								<span class="order-total tabular">{eur.format(o.total)}</span>
							</div>
							{#if o.note}<p class="order-note">{o.note}</p>{/if}
							<p class="order-code code">{o.code}</p>
						</li>
					{/each}
				</ul>
			</section>
		{/each}
	</div>
	<p class="sr-only" aria-live="polite">
		{byLane.AUTO_APPROVE.length} orders the agent decides alone, {byLane.NEEDS_HUMAN.length} wait for
		a person, {byLane.REJECT.length} are never ordered.
	</p>
</div>

<style>
	.playground {
		--pg-ok: var(--ok-tone, oklch(0.74 0.12 158));
		--pg-hold: var(--hold-tone, oklch(0.8 0.12 80));
		--pg-stop: var(--stop-tone, oklch(0.7 0.16 32));
		--pg-gold: oklch(0.84 0.085 86);
		--pg-ink: oklch(0.24 0.03 60);
		--pg-ink-soft: oklch(0.42 0.03 60);
		display: grid;
		gap: 1.5rem;
		margin-top: 2.5rem;
	}

	/* Charter: a vellum leaf with a gold hairline, on the night sky */
	.charter {
		position: relative;
		padding: 1.5rem 1.5rem 1.25rem;
		border-radius: 1.25rem;
		background: oklch(0.97 0.018 85);
		color: var(--pg-ink);
		box-shadow:
			0 0 0 1px oklch(0.84 0.085 86 / 0.6),
			0 0 0 6px oklch(0.97 0.018 85 / 0.06),
			0 30px 60px -30px oklch(0 0 0 / 0.6);
	}
	@media (min-width: 640px) {
		.charter {
			padding: 1.75rem 2rem 1.5rem;
		}
	}
	.charter-head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 0.75rem;
		font-size: 0.8125rem;
		color: var(--pg-ink-soft);
	}
	.seal {
		padding: 0.15rem 0.6rem;
		border-radius: 999px;
		background: var(--vermilion, oklch(0.52 0.16 32));
		color: oklch(0.97 0.018 85);
		font-size: 0.6875rem;
		font-weight: 600;
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}
	.charter-head .code {
		color: var(--pg-ink);
		font-weight: 500;
	}
	.charter-note {
		flex-basis: 100%;
	}
	@media (min-width: 720px) {
		.charter-note {
			flex-basis: auto;
			margin-left: auto;
		}
	}
	.writ {
		margin-top: 1rem;
		font-family: var(--font-display);
		font-size: clamp(1.1875rem, 2.1vw, 1.4375rem);
		line-height: 1.5;
		text-wrap: pretty;
	}
	.val {
		background: none;
		color: inherit;
		font-weight: 600;
		box-shadow: inset 0 -0.35em 0 oklch(0.84 0.085 86 / 0.55);
		border-radius: 2px;
		padding-inline: 0.1em;
	}
	.val:global(.flash) {
		animation: flash 900ms ease-out;
	}
	@keyframes flash {
		from {
			box-shadow: inset 0 -1.2em 0 oklch(0.84 0.085 86 / 0.9);
		}
	}

	.controls {
		display: grid;
		gap: 1rem 1.5rem;
		margin-top: 1.25rem;
		padding-top: 1.25rem;
		border-top: 1px solid oklch(0.24 0.03 60 / 0.1);
		font-family: var(--font-sans);
	}
	@media (min-width: 640px) {
		.controls {
			grid-template-columns: 1fr 1fr;
		}
	}
	.slider {
		display: grid;
		gap: 0.375rem;
	}
	.slider-label {
		display: flex;
		justify-content: space-between;
		font-size: 0.8125rem;
		color: var(--pg-ink-soft);
	}
	.slider-label output {
		font-weight: 600;
		color: var(--pg-ink);
	}
	input[type='range'] {
		width: 100%;
		accent-color: oklch(0.55 0.11 68);
		cursor: pointer;
	}
	.toggles,
	.segmented {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.375rem;
	}
	.toggles button,
	.segmented button {
		padding: 0.35rem 0.8rem;
		border-radius: 999px;
		border: 1px solid oklch(0.24 0.03 60 / 0.15);
		font-size: 0.8125rem;
		color: var(--pg-ink-soft);
		cursor: pointer;
		transition:
			background-color 200ms,
			color 200ms,
			border-color 200ms;
	}
	.toggles button:hover,
	.segmented button:hover {
		border-color: oklch(0.24 0.03 60 / 0.35);
		color: var(--pg-ink);
	}
	.toggles button[aria-pressed='true'],
	.segmented button[aria-checked='true'] {
		background: var(--lapis-night, oklch(0.16 0.05 270));
		border-color: var(--lapis-night, oklch(0.16 0.05 270));
		color: oklch(0.97 0.018 85);
	}
	.toggles button[aria-pressed='true']::before {
		content: '✓ ';
	}
	.segmented-label {
		margin-right: 0.25rem;
		font-size: 0.8125rem;
		color: var(--pg-ink-soft);
	}
	.charter :global(:focus-visible) {
		outline: 2px solid oklch(0.55 0.11 68);
		outline-offset: 2px;
	}

	/* Lanes: the three policy outcomes */
	.lanes {
		display: grid;
		gap: 0.75rem;
	}
	@media (min-width: 720px) {
		.lanes {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}
	}
	.lane {
		min-height: 9rem;
		padding: 0.875rem;
		border-radius: 1rem;
		background: oklch(1 0 0 / 0.035);
		box-shadow: inset 0 0 0 1px oklch(1 0 0 / 0.08);
	}
	.lane header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--on-night, oklch(0.94 0.02 85));
	}
	.dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: var(--tone);
		box-shadow: 0 0 0 3px color-mix(in oklch, var(--tone) 22%, transparent);
	}
	.lane-ok {
		--tone: var(--pg-ok);
	}
	.lane-hold {
		--tone: var(--pg-hold);
	}
	.lane-stop {
		--tone: var(--pg-stop);
	}
	.lane-count {
		margin-left: auto;
		min-width: 1.5rem;
		padding: 0 0.4rem;
		border-radius: 999px;
		background: oklch(1 0 0 / 0.08);
		text-align: center;
		font-size: 0.75rem;
	}
	.lane-code {
		margin-top: 0.125rem;
		margin-left: 1rem;
		font-size: 0.6875rem;
		color: color-mix(in oklch, var(--tone) 80%, transparent);
	}
	.lane ul {
		display: grid;
		gap: 0.5rem;
		margin-top: 0.75rem;
	}
	.lane li {
		padding: 0.625rem 0.75rem;
		border-radius: 0.75rem;
		background: oklch(0.97 0.018 85 / 0.06);
		box-shadow:
			inset 0 0 0 1px oklch(1 0 0 / 0.07),
			inset 2px 0 0 var(--tone);
		color: var(--on-night, oklch(0.94 0.02 85));
	}
	.order-top {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.5rem;
		font-size: 0.875rem;
	}
	.order-name {
		font-weight: 500;
	}
	.order-total {
		font-size: 0.8125rem;
		color: var(--on-night-soft, oklch(0.94 0.02 85 / 0.72));
	}
	.order-note {
		margin-top: 0.125rem;
		font-size: 0.75rem;
		color: var(--on-night-soft, oklch(0.94 0.02 85 / 0.72));
	}
	.order-code {
		display: inline-block;
		margin-top: 0.375rem;
		padding: 0.05rem 0.4rem;
		border-radius: 0.35rem;
		background: color-mix(in oklch, var(--tone) 14%, transparent);
		color: var(--tone);
		font-size: 0.6875rem;
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	/* Feedback after a change: what moved glows gold, its reason flashes, counts bump. */
	.lane li:global(.arrived) {
		animation: arrive-glow 1.9s ease-out;
	}
	.lane li:global(.arrived) .order-code {
		animation: code-flash 1.9s ease-out;
	}
	@keyframes arrive-glow {
		0%,
		20% {
			background: oklch(0.97 0.018 85 / 0.14);
			box-shadow:
				inset 0 0 0 1px oklch(0.84 0.085 86 / 0.9),
				inset 2px 0 0 var(--tone),
				0 0 0 4px oklch(0.84 0.085 86 / 0.22),
				0 0 28px oklch(0.84 0.085 86 / 0.35);
		}
	}
	@keyframes code-flash {
		0%,
		25% {
			background: color-mix(in oklch, var(--tone) 45%, transparent);
			color: oklch(0.97 0.018 85);
		}
	}
	.lane-count:global(.bump) {
		animation: bump 650ms cubic-bezier(0.3, 1.6, 0.5, 1);
	}
	@keyframes bump {
		40% {
			transform: scale(1.35);
			background: color-mix(in oklch, var(--tone) 50%, transparent);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.lane-count:global(.bump) {
			animation-name: count-flash;
		}
		@keyframes count-flash {
			40% {
				background: color-mix(in oklch, var(--tone) 50%, transparent);
			}
		}
	}
</style>
