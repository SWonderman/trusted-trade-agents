<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import { Tween, prefersReducedMotion } from 'svelte/motion';
	import { cubicIn, cubicOut } from 'svelte/easing';
	import CheckIcon from '@lucide/svelte/icons/check';
	import PauseIcon from '@lucide/svelte/icons/pause';
	import PlayIcon from '@lucide/svelte/icons/play';
	import BotIcon from '@lucide/svelte/icons/bot';

	/**
	 * "How one order travels", as one animated diagram: the order moves from the
	 * buyer's agent through Saint Elmo to Valio Aimo, forks at the policy, waits for a
	 * person and is placed, while the audit trail writes itself underneath.
	 *
	 * It plays once it scrolls into view and loops, pauses off-screen and in hidden
	 * tabs, and can be paused or stepped by hand. With reduced motion it shows the
	 * finished journey, still. The step list carries all the text for screen readers.
	 */

	const steps = [
		{
			n: 'I',
			title: 'The request',
			text: 'The buyer tells their agent what the kitchen needs, in plain words.'
		},
		{
			n: 'II',
			title: 'The search',
			text: 'The agent searches by what products declare. Unknown never counts as free-from.'
		},
		{
			n: 'III',
			title: 'The offer',
			text: 'Live price and stock for a shortlist, each figure with its source and expiry.'
		},
		{
			n: 'IV',
			title: 'The quote',
			text: 'Saint Elmo turns litres into the cases Valio Aimo sells, and shows its working.'
		},
		{
			n: 'V',
			title: 'The judgement',
			text: 'Plain code checks the quote against the mandate: approve, ask a person, or reject.'
		},
		{
			n: 'VI',
			title: 'The order',
			text: 'A person signs off on their own screen. Price and stock are checked again, then it’s placed.'
		}
	];

	const ledger = [
		['agent', 'dairy-restock', 'request received'],
		['tool', 'search_products', '12 products, FREE_FROM_LACTOSE'],
		['tool', 'get_offers', '4 live offers'],
		['tool', 'create_quote', 'Q-0398 · €1,840'],
		['policy', 'NEEDS_HUMAN', 'OVER_AUTO_APPROVE_LIMIT'],
		['person', 'approved', 'ORD-0142 → PLACED']
	] as const;

	const STEP_MS = 2900;
	const HOLD_MS = 3600;
	const BLANK_MS = 700;
	const ARRIVE = 850; // ms, about when the travelling order reaches its stop
	const LAST = steps.length - 1;

	// Diagram coordinates, in the SVG's 720 × 440 viewBox.
	const P = {
		agent: [110, 200],
		gate: [360, 200],
		aimo: [610, 200],
		human: [360, 352]
	} as const;
	type Point = keyof typeof P;
	const at = (x: number, y: number) => `left:${(x / 720) * 100}%;top:${(y / 440) * 100}%`;

	// Server render and no-JS: the finished journey. The browser takes over from there.
	let stage = $state(LAST);
	let playing = $state(false);
	let inView = $state(false);
	let pageVisible = $state(true);
	let started = false;
	// Visitors who prefer reduced motion never get autoplay, but may press Play.
	let optedIn = $state(false);

	let reduced = $derived(prefersReducedMotion.current && !optedIn);
	let d = $derived(reduced ? 0 : 1); // multiplies every duration

	$effect(() => {
		if (!playing || !inView || !pageVisible) return;
		const wait = stage === -1 ? BLANK_MS : stage === LAST ? HOLD_MS : STEP_MS;
		const id = setTimeout(() => (stage = stage === LAST ? -1 : stage + 1), wait);
		return () => clearTimeout(id);
	});

	function watch(node: HTMLElement) {
		const autoplay = !matchMedia('(prefers-reduced-motion: reduce)').matches;
		if (autoplay) stage = -1;
		const io = new IntersectionObserver(
			([entry]) => {
				inView = entry.isIntersecting;
				if (autoplay && inView && !started) {
					started = true;
					playing = true;
				}
			},
			{ threshold: 0.35 }
		);
		io.observe(node);
		return () => io.disconnect();
	}

	function goTo(i: number) {
		stage = i;
		started = true;
	}

	// The packet follows waypoints along the track, never cutting across the diagram.
	const routes: Record<number, Point[]> = {
		0: ['agent'],
		1: ['agent', 'gate'],
		2: ['gate', 'aimo'],
		3: ['aimo', 'gate'],
		4: ['gate', 'human'],
		5: ['human', 'gate', 'aimo']
	};
	function packet(node: SVGGElement) {
		$effect(() => {
			const route = routes[stage];
			if (!route) return;
			const frames = route.map((p) => ({ transform: `translate(${P[p][0]}px, ${P[p][1]}px)` }));
			const anim = node.animate(frames, {
				duration: frames.length > 1 ? 1100 * d : 0,
				easing: 'cubic-bezier(0.6, 0, 0.25, 1)',
				fill: 'forwards'
			});
			return () => anim.cancel();
		});
	}

	// Typed request, ticking offer figures.
	const request = '1,000 L of lactose-free milk by Monday';
	const typed = Tween.of(() => (stage >= 0 ? request.length : 0), {
		duration: () => (stage >= 0 ? 1400 * d : 0)
	});
	// The figures start ticking as their card appears.
	const price = Tween.of(() => (stage >= 2 ? 1.84 : 0), {
		get delay() {
			return ARRIVE * d;
		},
		duration: () => 1000 * d,
		easing: cubicOut
	});
	const stock = Tween.of(() => (stage >= 2 ? 64 : 0), {
		get delay() {
			return ARRIVE * d;
		},
		duration: () => 1000 * d,
		easing: cubicOut
	});

	/**
	 * Info cards rise in out of a soft blur as the order reaches their node, and
	 * drift up as they leave. Transforms only: positioning uses the CSS `translate`
	 * property, so the two never fight.
	 */
	function popIn(_node: Element, { delay = 0 } = {}) {
		return {
			delay: delay * d,
			duration: 520 * d,
			easing: cubicOut,
			css: (t: number, u: number) =>
				`opacity: ${t}; transform: translateY(${u * 12}px) scale(${0.94 + 0.06 * t}); filter: blur(${u * 6}px);`
		};
	}
	function popOut(_node: Element, { duration = 260 } = {}) {
		return {
			duration: duration * d,
			easing: cubicIn,
			css: (t: number, u: number) =>
				`opacity: ${t}; transform: translateY(${-u * 8}px) scale(${0.98 + 0.02 * t}); filter: blur(${u * 4}px);`
		};
	}

	// Where the order is now, and where it has been. A stage's last waypoint is its stop.
	let here = $derived<Point | null>(routes[stage]?.at(-1) ?? null);
	const firstVisit: Record<Point, number> = { agent: 0, gate: 1, aimo: 2, human: 4 };
	const visited = (p: Point) => stage >= firstVisit[p];

	let gateCallout = $derived(stage === 1 ? 'search' : stage === 3 ? 'quote' : null);
	let ledgerLines = $derived(
		ledger
			.slice(0, stage + 1)
			.slice(-4)
			.toReversed()
	);
</script>

<svelte:document
	onvisibilitychange={() => (pageVisible = document.visibilityState === 'visible')}
/>

<div class="journey" data-motion={optedIn ? 'allowed' : undefined} {@attach watch}>
	<!-- The words: a step list that doubles as the controls. -->
	<div class="rail">
		<ol class="steps">
			{#each steps as s, i (s.n)}
				<li class={[i === stage && 'active', i < stage && 'done']}>
					<button
						type="button"
						onclick={() => goTo(i)}
						aria-current={i === stage ? 'step' : undefined}
					>
						<span class="numeral" aria-hidden="true">{s.n}</span>
						<span class="title">{s.title}</span>
					</button>
					<div class="caption">
						<p>{s.text}</p>
					</div>
					{#if i === stage && playing && inView && !reduced}
						{#key `${stage}-${playing}`}
							<span class="progress" style:--ms="{STEP_MS}ms" aria-hidden="true"></span>
						{/key}
					{/if}
				</li>
			{/each}
		</ol>
		<button
			type="button"
			class="toggle"
			onclick={() => {
				started = true;
				if (!optedIn && prefersReducedMotion.current) {
					// An explicit request for motion: replay the journey from the start.
					optedIn = true;
					playing = true;
					stage = -1;
					return;
				}
				playing = !playing;
				if (playing && stage === -1) stage = 0;
			}}
		>
			{#if playing}<PauseIcon />Pause{:else}<PlayIcon />{reduced ? 'Play the journey' : 'Play'}{/if}
		</button>
	</div>

	<!-- The picture. Decorative: the step list above says the same in words. -->
	<div class="stage" aria-hidden="true">
		<div class="canvas">
			<svg viewBox="0 0 720 440" class="lines">
				<defs>
					<clipPath id="gate-clip"><circle cx="360" cy="200" r="38" /></clipPath>
				</defs>

				<!-- The track, faint, always there -->
				<g class="track">
					<path d="M110 200 H610" />
					<path d="M360 200 C360 290 200 280 200 352" />
					<path d="M360 200 V352" />
					<path d="M360 200 C360 290 520 280 520 352" />
				</g>

				<!-- The route, drawn in gold as the order travels -->
				<path class={['route', stage >= 1 && 'on']} d="M110 200 H360" pathLength="1" />
				<path class={['route', stage >= 2 && 'on']} d="M360 200 H610" pathLength="1" />
				<path
					class={['route', 'fork', 'dim', stage >= 4 && 'on']}
					d="M360 200 C360 290 200 280 200 352"
					pathLength="1"
				/>
				<path
					class={['route', 'fork', 'hold', stage >= 4 && 'on']}
					d="M360 200 V352"
					pathLength="1"
				/>
				<path
					class={['route', 'fork', 'dim', stage >= 4 && 'on']}
					d="M360 200 C360 290 520 280 520 352"
					pathLength="1"
				/>

				<!-- The order itself: it travels behind the nodes, so it disappears into each one it reaches. -->
				<g {@attach packet} class={['packet', stage >= 0 && 'shown', stage === 5 && 'placed']}>
					<circle r="15" class="packet-glow" />
					<circle r="6.5" class="packet-core" />
				</g>

				<!-- Arrival glows: the node the order has just reached lights up, softly. -->
				<circle class={['glow', here === 'agent' && 'on']} cx="110" cy="200" r="36" />
				<circle class={['glow', here === 'gate' && 'on']} cx="360" cy="200" r="54" />
				<rect
					class={['glow', here === 'aimo' && 'on']}
					x="548"
					y="166"
					width="124"
					height="68"
					rx="20"
				/>
				<circle class={['glow', 'glow-hold', here === 'human' && 'on']} cx="360" cy="352" r="20" />

				<!-- Nodes -->
				<circle
					class={['node', visited('agent') && 'visited', here === 'agent' && 'here']}
					cx="110"
					cy="200"
					r="30"
				/>
				<circle class={['gate-ring', here === 'gate' && 'here']} cx="360" cy="200" r="46" />
				<circle class={['halo', here === 'gate' && 'pulse']} cx="360" cy="200" r="46" />
				<image
					href="/art/erasmus-roundel-192.webp"
					x="322"
					y="162"
					width="76"
					height="76"
					clip-path="url(#gate-clip)"
				/>
				<rect
					class={['node', visited('aimo') && 'visited', here === 'aimo' && 'here']}
					x="556"
					y="174"
					width="108"
					height="52"
					rx="14"
				/>
				<image href="/brand/valio-aimo-wordmark.png" x="572" y="183" width="76" height="34" />

				<circle class={['outcome', 'ok', stage >= 4 && 'shown']} cx="200" cy="352" r="9" />
				<circle
					class={['outcome', 'hold', stage >= 4 && 'shown', 'chosen']}
					cx="360"
					cy="352"
					r="11"
				/>
				<circle class={['outcome', 'stop', stage >= 4 && 'shown']} cx="520" cy="352" r="9" />
			</svg>

			<!-- Labels and cards, in HTML for crisp type -->
			<span class="label" style={at(110, 248)}>
				<span class="code">dairy-restock</span>
			</span>
			<span class="agent-icon" style={at(110, 200)}><BotIcon /></span>
			<span class="label strong" style={at(360, 266)}>Saint Elmo</span>

			{#if stage >= 0}
				<div class={['bubble', stage >= 1 && 'past']} style={at(70, 70)} in:popIn out:popOut>
					<span class="bubble-who">Buyer, to their agent</span>
					<span class="bubble-text"
						>“{request.slice(0, Math.round(typed.current))}<span
							class={['caret', typed.current >= request.length && 'done']}>|</span
						>”</span
					>
				</div>
			{/if}

			{#if gateCallout === 'search'}
				<div class="card above" style={at(410, 128)} in:popIn={{ delay: ARRIVE }} out:popOut>
					<span class="card-tool code">search_products</span>
					<span class="chip code">FREE_FROM_LACTOSE</span>
					<span class="card-meta">12 products declare it</span>
				</div>
			{/if}
			{#if gateCallout === 'quote'}
				<div class="card above" style={at(410, 128)} in:popIn={{ delay: ARRIVE }} out:popOut>
					<span class="card-tool code">create_quote</span>
					<span class="card-big tabular">1,000 L → 50 KI</span>
					<span class="card-meta">1 KI ≈ 20 L, lot size 1</span>
				</div>
			{/if}

			{#if stage >= 2}
				<div class="card above" style={at(610, 128)} in:popIn={{ delay: ARRIVE }} out:popOut>
					<span class="card-tool code">get_offers</span>
					<span class="card-big tabular">€{price.current.toFixed(2)} <small>per litre</small></span>
					<span class="card-meta tabular">{Math.round(stock.current)} KI in stock by Monday</span>
				</div>
			{/if}

			{#if stage >= 4}
				<span
					class="label tiny dimmed"
					style={at(200, 380)}
					in:fade={{ delay: 700 * d, duration: 300 * d }}
					out:fade={{ duration: 200 * d }}><span class="code">AUTO_APPROVE</span></span
				>
				<span
					class="label tiny dimmed"
					style={at(520, 380)}
					in:fade={{ delay: 700 * d, duration: 300 * d }}
					out:fade={{ duration: 200 * d }}><span class="code">REJECT</span></span
				>
				<div class="card side" style={at(548, 352)} in:popIn={{ delay: 950 }} out:popOut>
					<span class="card-status"><span class="dot"></span>Needs a person</span>
					<span class="chip hold code">OVER_AUTO_APPROVE_LIMIT</span>
					<span class="card-meta tabular">€1,840 &gt; €1,500 auto-approve</span>
				</div>
			{/if}

			{#if stage >= 5}
				<div class="approve" style={at(360, 398)} in:popIn={{ delay: 250 }} out:popOut>
					<CheckIcon /> Approved by Helmi
				</div>
				<span class="placed code" style={at(610, 252)} in:popIn={{ delay: 1100 }} out:popOut
					>PLACED</span
				>
			{/if}
		</div>

		<div class="ledger">
			<p class="ledger-head">
				<span>Audit trail</span>
				<span class="ledger-note">append-only</span>
			</p>
			<ol>
				{#each ledgerLines as line (line[1])}
					<li in:fly={{ y: -10, duration: 400 * d }}>
						<span class="who">{line[0]}</span>
						<span class="what code">{line[1]}</span>
						<span class="why">{line[2]}</span>
					</li>
				{/each}
			</ol>
		</div>
	</div>
</div>

<style>
	.journey {
		/* Outcome tones that hold contrast on ivory */
		--j-ok: oklch(0.56 0.12 158);
		--j-hold: oklch(0.64 0.14 68);
		--j-stop: oklch(0.56 0.17 32);
		/* Soft, bright lines: champagne gold for the route, a light warm grey for the rest. */
		--j-line: oklch(0.6 0.02 85 / 0.22);
		--j-edge: oklch(0.6 0.02 85 / 0.28);
		--j-gold: oklch(0.84 0.085 86);
		--j-gold-soft: oklch(0.84 0.085 86 / 0.75);
		/* A brighter amber for the chosen branch; text keeps the deeper --j-hold. */
		--j-hold-bright: oklch(0.8 0.12 76);
		--j-ink: var(--ink, oklch(0.24 0.03 60));
		--j-ink-soft: var(--ink-soft, oklch(0.42 0.03 60));
		/* Roughly when the travelling order reaches its stop (packet animation is 1100ms). */
		--arrive: 850ms;

		display: grid;
		gap: 2rem;
		margin-top: 3.5rem;
	}
	@media (min-width: 1024px) {
		.journey {
			grid-template-columns: 19rem minmax(0, 1fr);
			gap: 3.5rem;
			align-items: center;
		}
	}

	/* Step list */
	.rail {
		order: 2;
	}
	@media (min-width: 1024px) {
		.rail {
			order: 0;
		}
	}
	.steps {
		display: grid;
		gap: 0.25rem;
	}
	.steps li {
		position: relative;
		border-radius: 0.875rem;
		transition: background-color 300ms;
	}
	.steps li.active {
		background: oklch(1 0 0 / 0.65);
		box-shadow: 0 0 0 1px oklch(0.24 0.03 60 / 0.07);
	}
	.steps button {
		display: flex;
		align-items: baseline;
		gap: 0.875rem;
		width: 100%;
		padding: 0.625rem 1rem;
		text-align: left;
		cursor: pointer;
		color: var(--j-ink-soft);
		transition: color 200ms;
	}
	.steps button:hover,
	.steps li.active button {
		color: var(--j-ink);
	}
	.numeral {
		width: 1.75rem;
		font-family: var(--font-display);
		font-style: italic;
		font-size: 1.25rem;
		color: oklch(0.52 0.16 32 / 0.55);
		transition: color 300ms;
	}
	.steps li.active .numeral,
	.steps li.done .numeral {
		color: var(--vermilion, oklch(0.52 0.16 32));
	}
	.title {
		font-weight: 600;
		font-size: 0.9375rem;
	}
	/* Every caption stays in the DOM for screen readers; only the active one opens. */
	.caption {
		display: grid;
		grid-template-rows: 0fr;
		transition: grid-template-rows 400ms cubic-bezier(0.2, 0.7, 0.2, 1);
	}
	.caption p {
		overflow: hidden;
		padding-inline: 3.625rem 1rem;
		font-size: 0.9375rem;
		line-height: 1.55;
		color: var(--j-ink-soft);
	}
	.steps li.active .caption {
		grid-template-rows: 1fr;
	}
	.steps li.active .caption p {
		padding-bottom: 0.875rem;
	}
	.progress {
		position: absolute;
		left: 1rem;
		right: 1rem;
		bottom: 0;
		height: 2px;
		border-radius: 2px;
		background: var(--j-gold);
		transform-origin: left;
		animation: fill var(--ms) linear both;
	}
	@keyframes fill {
		from {
			transform: scaleX(0);
		}
		to {
			transform: scaleX(1);
		}
	}
	.toggle {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		margin: 1rem 0 0 1rem;
		padding: 0.3rem 0.75rem;
		border-radius: 999px;
		border: 1px solid oklch(0.24 0.03 60 / 0.15);
		font-size: 0.8125rem;
		color: var(--j-ink-soft);
		cursor: pointer;
	}
	.toggle:hover {
		color: var(--j-ink);
		border-color: oklch(0.24 0.03 60 / 0.3);
	}
	.toggle :global(svg) {
		width: 0.875rem;
		height: 0.875rem;
	}

	/* Stage */
	.stage {
		position: relative;
		overflow: hidden;
		border-radius: 1.5rem;
		background:
			radial-gradient(ellipse 50% 45% at 50% 42%, oklch(0.9 0.07 82 / 0.35), transparent 70%),
			linear-gradient(oklch(0.24 0.03 60 / 0.035) 1px, transparent 1px) 0 0 / 100% 2rem,
			linear-gradient(90deg, oklch(0.24 0.03 60 / 0.035) 1px, transparent 1px) 0 0 / 2rem 100%,
			oklch(0.99 0.006 85);
		box-shadow:
			0 0 0 1px oklch(0.24 0.03 60 / 0.08),
			0 40px 80px -50px oklch(0.35 0.06 60 / 0.45);
		container-type: inline-size;
	}
	.canvas {
		position: relative;
		aspect-ratio: 720 / 440;
		font-size: clamp(0.5625rem, 1.75cqi, 0.8125rem);
		color: var(--j-ink);
	}
	.lines {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
	}
	.track path {
		fill: none;
		stroke: var(--j-line);
		stroke-width: 1.5;
		stroke-dasharray: 3 5;
	}
	.route {
		fill: none;
		stroke: var(--j-gold);
		stroke-width: 3;
		stroke-linecap: round;
		stroke-dasharray: 1;
		stroke-dashoffset: 1;
		transition: stroke-dashoffset 1000ms cubic-bezier(0.6, 0, 0.25, 1);
	}
	.route.on {
		stroke-dashoffset: 0;
	}
	.route.fork.dim {
		stroke: var(--j-edge);
		stroke-width: 1.5;
	}
	.route.fork.hold {
		stroke: var(--j-hold-bright);
	}
	.node {
		fill: oklch(1 0 0);
		stroke: var(--j-edge);
		stroke-width: 1.25;
		transition:
			stroke 400ms,
			filter 400ms;
	}
	.node.visited {
		stroke: var(--j-gold-soft);
	}
	/* The highlight lands as the order arrives, not as it sets off. */
	.node.here {
		stroke: var(--j-gold);
		stroke-width: 1.75;
		transition-delay: var(--arrive);
	}
	.glow {
		fill: oklch(0.85 0.1 82 / 0.5);
		filter: blur(10px);
		opacity: 0;
		transition: opacity 500ms;
	}
	.glow.on {
		opacity: 1;
		transition: opacity 700ms var(--arrive);
	}
	.glow-hold {
		fill: oklch(0.8 0.13 70 / 0.5);
	}
	.gate-ring {
		fill: oklch(1 0 0);
		stroke: var(--j-gold);
		stroke-width: 2;
		filter: drop-shadow(0 10px 18px oklch(0.35 0.06 60 / 0.25));
		transition: stroke-width 400ms;
	}
	.gate-ring.here {
		stroke-width: 2.75;
		transition-delay: var(--arrive);
	}
	.halo {
		fill: none;
		stroke: oklch(0.78 0.11 268 / 0.6);
		stroke-width: 2;
		opacity: 0;
		transform-origin: 360px 200px;
	}
	.halo.pulse {
		animation: halo 2.4s ease-out var(--arrive) infinite;
	}
	@keyframes halo {
		from {
			opacity: 0.6;
			transform: scale(1);
		}
		to {
			opacity: 0;
			transform: scale(1.35);
		}
	}
	.outcome {
		opacity: 0;
		transform-box: fill-box;
		transform-origin: center;
		transform: scale(0.4);
		transition:
			opacity 400ms 600ms,
			transform 500ms 600ms cubic-bezier(0.3, 1.5, 0.5, 1);
	}
	.outcome.shown {
		opacity: 0.35;
		transform: scale(1);
	}
	.outcome.chosen.shown {
		opacity: 1;
	}
	.outcome.ok {
		fill: var(--j-ok);
	}
	.outcome.hold {
		fill: var(--j-hold-bright);
	}
	.outcome.stop {
		fill: var(--j-stop);
	}
	.packet {
		opacity: 0;
		transition: opacity 300ms;
	}
	.packet.shown {
		opacity: 1;
	}
	.packet-glow {
		fill: oklch(0.85 0.09 82 / 0.45);
		animation: breathe 1.8s ease-in-out infinite;
	}
	.packet-core {
		fill: var(--lapis-night, oklch(0.16 0.05 270));
		stroke: oklch(1 0 0);
		stroke-width: 2;
	}
	.packet.placed .packet-core {
		fill: var(--j-ok);
	}
	@keyframes breathe {
		50% {
			transform: scale(1.35);
			opacity: 0.6;
		}
	}

	/* Overlays: positioned by their centre on the viewBox coordinates */
	.label,
	.agent-icon,
	.card,
	.bubble,
	.approve,
	.placed {
		position: absolute;
		translate: -50% -50%;
		white-space: nowrap;
	}
	.label {
		font-size: 0.95em;
		color: var(--j-ink-soft);
	}
	.label.strong {
		font-family: var(--font-display);
		font-size: 1.35em;
		font-weight: 500;
		color: var(--j-ink);
	}
	.label.tiny {
		font-size: 0.8em;
	}
	.label.dimmed {
		opacity: 0.55;
	}
	.agent-icon {
		display: grid;
		place-items: center;
		color: var(--j-ink);
	}
	.agent-icon :global(svg) {
		width: 2em;
		height: 2em;
	}
	.bubble {
		translate: 0 -50%;
		display: grid;
		gap: 0.25em;
		max-width: 36%;
		padding: 0.7em 0.95em;
		border-radius: 1em 1em 1em 0.25em;
		background: var(--lapis-night, oklch(0.16 0.05 270));
		color: oklch(0.96 0.015 85);
		box-shadow: 0 14px 30px -18px oklch(0.16 0.05 270 / 0.7);
		white-space: normal;
		transition:
			opacity 300ms,
			translate 300ms;
	}
	.bubble-who {
		font-size: 0.85em;
		opacity: 0.65;
	}
	.bubble-text {
		font-family: var(--font-display);
		font-size: 1.3em;
		line-height: 1.2;
	}
	.caret {
		margin-left: 1px;
		color: var(--j-gold);
		animation: caret 0.9s steps(1) infinite;
	}
	.caret.done {
		opacity: 0;
		animation: none;
	}
	@keyframes caret {
		50% {
			opacity: 0;
		}
	}
	.card {
		display: grid;
		justify-items: start;
		gap: 0.35em;
		padding: 0.75em 0.9em;
		border-radius: 0.85em;
		background: oklch(1 0 0 / 0.92);
		box-shadow:
			0 0 0 1px oklch(0.24 0.03 60 / 0.09),
			0 16px 32px -20px oklch(0.35 0.06 60 / 0.5);
		backdrop-filter: blur(6px);
	}
	.card.above {
		translate: -50% -100%;
	}
	.card.side {
		translate: 0 -50%;
	}
	.card-tool {
		font-size: 0.85em;
		color: var(--j-ink-soft);
	}
	.card-big {
		font-size: 1.25em;
		font-weight: 600;
		letter-spacing: -0.01em;
	}
	.card-big small {
		font-size: 0.65em;
		font-weight: 400;
		color: var(--j-ink-soft);
	}
	.card-meta {
		font-size: 0.85em;
		color: var(--j-ink-soft);
	}
	.card-status {
		display: inline-flex;
		align-items: center;
		gap: 0.45em;
		font-weight: 600;
	}
	.dot {
		width: 0.55em;
		height: 0.55em;
		border-radius: 50%;
		background: var(--j-hold);
		box-shadow: 0 0 0 0.25em oklch(0.64 0.14 68 / 0.2);
	}
	.chip {
		padding: 0.15em 0.5em;
		border-radius: 0.4em;
		background: var(--lapis-night, oklch(0.16 0.05 270));
		color: oklch(0.96 0.015 85);
		font-size: 0.8em;
	}
	.chip.hold {
		background: oklch(0.64 0.14 68 / 0.14);
		color: oklch(0.48 0.12 60);
	}
	.approve {
		translate: -50% -50%;
		display: inline-flex;
		align-items: center;
		gap: 0.35em;
		padding: 0.35em 0.75em 0.35em 0.55em;
		border-radius: 999px;
		background: var(--j-ink);
		color: oklch(0.97 0.01 85);
		font-weight: 600;
	}
	.approve :global(svg) {
		width: 1.1em;
		height: 1.1em;
		color: oklch(0.8 0.13 158);
	}
	.placed {
		padding: 0.2em 0.6em;
		border-radius: 999px;
		background: oklch(0.56 0.12 158 / 0.12);
		color: oklch(0.42 0.1 158);
		font-weight: 500;
	}

	/* Audit trail */
	.ledger {
		border-top: 1px solid oklch(0.24 0.03 60 / 0.08);
		background: oklch(0.975 0.012 85 / 0.85);
		padding: 0.875rem 1.25rem 1rem;
		font-size: 0.8125rem;
	}
	.ledger-head {
		display: flex;
		justify-content: space-between;
		font-size: 0.6875rem;
		font-weight: 600;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--j-ink-soft);
	}
	.ledger-note {
		font-weight: 400;
		letter-spacing: 0.04em;
		text-transform: none;
		opacity: 0.8;
	}
	.ledger ol {
		display: grid;
		gap: 0.25rem;
		height: 5.5rem;
		margin-top: 0.5rem;
		overflow: hidden;
		mask-image: linear-gradient(to bottom, black 60%, transparent);
	}
	.ledger li {
		display: grid;
		grid-template-columns: 3.75rem auto minmax(0, 1fr);
		gap: 0.75rem;
		align-items: baseline;
		white-space: nowrap;
	}
	.ledger li:first-child .what {
		color: var(--j-ink);
		font-weight: 500;
	}
	.who {
		font-size: 0.75rem;
		color: var(--vermilion, oklch(0.52 0.16 32));
	}
	.what {
		color: var(--j-ink-soft);
	}
	.why {
		overflow: hidden;
		text-overflow: ellipsis;
		color: var(--j-ink-soft);
	}

	/*
	 * Small screens: type has a floor, so the diagram keeps only the essentials. The
	 * policy reason is still in the audit trail right below, and in the step caption.
	 */
	@container (max-width: 560px) {
		.card.side,
		.card-meta,
		.bubble-who,
		.label.tiny {
			display: none;
		}
		.bubble.past {
			opacity: 0;
			translate: 0 -70%;
		}
		.card {
			padding: 0.5em 0.65em;
		}
	}

	/* Still, unless the visitor pressed Play (data-motion="allowed"). */
	@media (prefers-reduced-motion: reduce) {
		.journey:not([data-motion='allowed']) {
			--arrive: 0ms;
		}
		.journey:not([data-motion='allowed']) :is(.route, .outcome, .caption, .packet) {
			transition: none;
		}
		.journey:not([data-motion='allowed']) :is(.halo.pulse, .packet-glow, .caret) {
			animation: none;
		}
	}
</style>
