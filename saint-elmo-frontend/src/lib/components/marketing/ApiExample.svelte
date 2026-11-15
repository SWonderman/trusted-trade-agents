<script lang="ts">
	import { prefersReducedMotion } from 'svelte/motion';
	import PauseIcon from '@lucide/svelte/icons/pause';
	import PlayIcon from '@lucide/svelte/icons/play';

	/**
	 * "One API, two doors", acted out: the same three calls through MCP or REST, with
	 * the request typing itself and the response streaming in. The responses are the
	 * same through both doors, because the same backend answers both.
	 *
	 * Plays in view and loops, switching door after each round; pauses off-screen.
	 * With reduced motion it shows one finished exchange and offers Play.
	 */

	type Door = 'mcp' | 'rest';
	type Tok = [text: string, cls?: 'k' | 's' | 'n' | 'm' | 'p' | 'c'];

	const scenes: {
		label: string;
		request: Record<Door, Tok[]>;
		response: Tok[][];
		status: string;
	}[] = [
		{
			label: 'Search',
			request: {
				mcp: [
					['tools/call ', 'm'],
					['search_products', 'p'],
					['\n{ "query": ', 'c'],
					['"lactose-free milk"', 's'],
					[',\n  "requiredClaims": [', 'c'],
					['"FREE_FROM LACTOSE"', 's'],
					['] }', 'c']
				],
				rest: [
					['POST ', 'm'],
					['/api/v1/products/search', 'p'],
					['\nAuthorization: Bearer ', 'c'],
					['se_ag_7f2a…', 's'],
					['\n{ "query": ', 'c'],
					['"lactose-free milk"', 's'],
					[' }', 'c']
				]
			},
			response: [
				[['{ '], ['"total"', 'k'], [': '], ['729', 'n'], [',']],
				[['  '], ['"items"', 'k'], [': [{']],
				[['    '], ['"code"', 'k'], [': '], ['"463038"', 's'], [',']],
				[['    '], ['"name"', 'k'], [': '], ['"Valio Eila® … 10 l lactose free"', 's'], [',']],
				[['    '], ['"claims"', 'k'], [': ['], ['"FREE_FROM LACTOSE"', 's'], [']']],
				[['  }] }']]
			],
			status: '200 · 729 products, unknown is never free-from'
		},
		{
			label: 'Order',
			request: {
				mcp: [
					['tools/call ', 'm'],
					['place_order', 'p'],
					['\n{ "quoteId": ', 'c'],
					['"Q-0398"', 's'],
					[' }', 'c']
				],
				rest: [
					['POST ', 'm'],
					['/api/v1/orders', 'p'],
					['\nAuthorization: Bearer ', 'c'],
					['se_ag_7f2a…', 's'],
					['\n{ "quoteId": ', 'c'],
					['"Q-0398"', 's'],
					[' }', 'c']
				]
			},
			response: [
				[['{ '], ['"orderId"', 'k'], [': '], ['"ORD-0142"', 's'], [',']],
				[['  '], ['"status"', 'k'], [': '], ['"PENDING_APPROVAL"', 's'], [',']],
				[
					['  '],
					['"policy"', 'k'],
					[': { '],
					['"outcome"', 'k'],
					[': '],
					['"NEEDS_HUMAN"', 's'],
					[',']
				],
				[['    '], ['"reasonCodes"', 'k'], [': ['], ['"OVER_AUTO_APPROVE_LIMIT"', 's'], ['] },']],
				[['  '], ['"checkAgainAfterSeconds"', 'k'], [': '], ['30', 'n'], [' }']]
			],
			status: 'Waits for a person. The agent never does: it checks back.'
		},
		{
			label: 'Status',
			request: {
				mcp: [
					['tools/call ', 'm'],
					['get_order_status', 'p'],
					['\n{ "orderId": ', 'c'],
					['"ORD-0142"', 's'],
					[' }', 'c']
				],
				rest: [
					['GET ', 'm'],
					['/api/v1/orders/ORD-0142', 'p'],
					['\nAuthorization: Bearer ', 'c'],
					['se_ag_7f2a…', 's']
				]
			},
			response: [
				[['{ '], ['"orderId"', 'k'], [': '], ['"ORD-0142"', 's'], [',']],
				[['  '], ['"status"', 'k'], [': '], ['"PLACED"', 's'], [',']],
				[['  '], ['"approvedBy"', 'k'], [': '], ['"Helmi Virtanen"', 's'], [',']],
				[
					['  '],
					['"total"', 'k'],
					[': { '],
					['"net"', 'k'],
					[': '],
					['1840.00', 'n'],
					[', '],
					['"currency"', 'k'],
					[': '],
					['"EUR"', 's'],
					[' } }']
				]
			],
			status: '200 · approved by a person, recorded in the audit trail'
		}
	];

	const TYPE_MS = 900;
	const LINE_MS = 140;
	const HOLD_MS = 2600;

	// Server render and no-JS: one finished exchange. The browser takes over from there.
	let door = $state<Door>('mcp');
	let scene = $state(1);
	let typed = $state(Infinity); // characters of the request shown
	let lines = $state(Infinity); // lines of the response shown
	let playing = $state(false);
	let inView = $state(false);
	let pageVisible = $state(true);
	let optedIn = $state(false);

	let current = $derived(scenes[scene]);
	let requestLength = $derived(current.request[door].reduce((n, [text]) => n + text.length, 0));

	/** The request tokens, cut off after `n` characters. */
	function sliceTokens(tokens: Tok[], n: number): Tok[] {
		const out: Tok[] = [];
		for (const [text, cls] of tokens) {
			if (n <= 0) break;
			out.push([text.slice(0, n), cls]);
			n -= text.length;
		}
		return out;
	}

	// One clock drives typing, streaming, holding and moving on.
	$effect(() => {
		if (!playing || !inView || !pageVisible) return;
		let id: ReturnType<typeof setTimeout>;
		if (typed < requestLength) {
			const step = Math.max(12, TYPE_MS / requestLength);
			id = setTimeout(() => (typed = Math.min(requestLength, typed + 2)), step * 2);
		} else if (lines < current.response.length) {
			id = setTimeout(() => (lines += 1), lines === 0 ? 350 : LINE_MS);
		} else {
			id = setTimeout(() => {
				const last = scene === scenes.length - 1;
				if (last) door = door === 'mcp' ? 'rest' : 'mcp';
				start(last ? 0 : scene + 1);
			}, HOLD_MS);
		}
		return () => clearTimeout(id);
	});

	function start(i: number) {
		scene = i;
		typed = 0;
		lines = 0;
	}

	function show(i: number) {
		if (playing) start(i);
		else {
			scene = i;
			typed = Infinity;
			lines = Infinity;
		}
	}

	function switchDoor(d: Door) {
		door = d;
		if (playing) start(scene);
	}

	function watch(node: HTMLElement) {
		const autoplay = !matchMedia('(prefers-reduced-motion: reduce)').matches;
		let started = false;
		const io = new IntersectionObserver(
			([entry]) => {
				inView = entry.isIntersecting;
				if (autoplay && inView && !started) {
					started = true;
					playing = true;
					start(0);
				}
			},
			{ threshold: 0.4 }
		);
		io.observe(node);
		return () => io.disconnect();
	}

	function togglePlay() {
		if (!optedIn && prefersReducedMotion.current) {
			optedIn = true;
			playing = true;
			start(0);
			return;
		}
		playing = !playing;
		if (playing && typed === Infinity) start(scene);
	}

	let shownRequest = $derived(sliceTokens(current.request[door], typed));
	let done = $derived(lines >= current.response.length);
</script>

<svelte:document
	onvisibilitychange={() => (pageVisible = document.visibilityState === 'visible')}
/>

<figure class="console" data-motion={optedIn ? 'allowed' : undefined} {@attach watch}>
	<div class="bar">
		<span class="lights" aria-hidden="true"><i></i><i></i><i></i></span>
		<div class="doors" role="radiogroup" aria-label="Door">
			<button
				type="button"
				role="radio"
				aria-checked={door === 'mcp'}
				onclick={() => switchDoor('mcp')}>MCP</button
			>
			<button
				type="button"
				role="radio"
				aria-checked={door === 'rest'}
				onclick={() => switchDoor('rest')}>REST</button
			>
		</div>
		<span class="who code">dairy-restock</span>
	</div>

	<div class="screen" aria-hidden="true">
		<p class="lane-label">{door === 'mcp' ? 'Agent → MCP server' : 'Agent → REST API'}</p>
		<pre class="request code"><code
				>{#each shownRequest as [text, cls], i (i)}<span class={cls}>{text}</span>{/each}<span
					class={['caret', typed >= requestLength && 'hidden']}>▍</span
				></code
			></pre>

		<p class="lane-label">← Saint Elmo</p>
		<pre class="response code"><code
				>{#each current.response.slice(0, lines) as line, i (`${scene}-${door}-${i}`)}<span
						class="line"
						>{#each line as [text, cls], j (j)}<span class={cls}>{text}</span>{/each}</span
					>{/each}</code
			></pre>
	</div>

	<div class="foot">
		<ol class="calls">
			{#each scenes as s, i (s.label)}
				<li>
					<button
						type="button"
						aria-current={i === scene ? 'step' : undefined}
						onclick={() => show(i)}
					>
						<span class="n tabular">{i + 1}</span>{s.label}
					</button>
				</li>
			{/each}
		</ol>
		<button type="button" class="play" onclick={togglePlay}>
			{#if playing}<PauseIcon />Pause{:else}<PlayIcon />Play{/if}
		</button>
	</div>

	<p class="sr-only">
		Example calls, through MCP or REST: search_products finds 729 lactose-free milk products;
		place_order returns PENDING_APPROVAL with policy outcome NEEDS_HUMAN and reason
		OVER_AUTO_APPROVE_LIMIT; get_order_status later returns PLACED, approved by a person.
		Illustrative; the orders API is still being built.
	</p>
	<figcaption class={['status', done && 'shown']}>{current.status}</figcaption>
</figure>

<style>
	.console {
		--c-bg: oklch(0.17 0.03 268);
		--c-line: oklch(1 0 0 / 0.08);
		--c-text: oklch(0.93 0.015 85);
		--c-soft: oklch(0.93 0.015 85 / 0.55);
		--c-key: oklch(0.8 0.09 266);
		--c-str: oklch(0.84 0.085 86);
		--c-num: oklch(0.8 0.12 158);
		--c-path: oklch(0.86 0.1 75);

		margin: 0;
		border-radius: 1.125rem;
		overflow: hidden;
		background: var(--c-bg);
		color: var(--c-text);
		box-shadow:
			0 0 0 1px oklch(0.24 0.03 60 / 0.12),
			0 50px 90px -45px oklch(0.25 0.05 60 / 0.55);
	}

	.bar {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		padding: 0.625rem 0.875rem;
		border-bottom: 1px solid var(--c-line);
		font-size: 0.75rem;
	}
	.lights {
		display: flex;
		gap: 0.375rem;
	}
	.lights i {
		width: 0.625rem;
		height: 0.625rem;
		border-radius: 50%;
		background: oklch(1 0 0 / 0.14);
	}
	.doors {
		display: flex;
		gap: 0.125rem;
		padding: 0.15rem;
		border-radius: 999px;
		background: oklch(1 0 0 / 0.06);
	}
	.doors button {
		padding: 0.2rem 0.75rem;
		border-radius: 999px;
		font-size: 0.75rem;
		font-weight: 600;
		letter-spacing: 0.04em;
		color: var(--c-soft);
		cursor: pointer;
		transition:
			background-color 250ms,
			color 250ms;
	}
	.doors button[aria-checked='true'] {
		background: var(--c-str);
		color: oklch(0.2 0.03 268);
	}
	.who {
		margin-left: auto;
		color: var(--c-soft);
	}

	.screen {
		display: grid;
		gap: 0.375rem;
		min-height: 20.5rem;
		padding: 1rem 1.25rem 1.25rem;
		align-content: start;
	}
	.lane-label {
		font-size: 0.6875rem;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--c-soft);
	}
	.lane-label:not(:first-child) {
		margin-top: 0.875rem;
	}
	pre {
		margin: 0;
		white-space: pre-wrap;
		word-break: break-word;
		font-size: 0.8125rem;
		line-height: 1.7;
	}
	@media (max-width: 480px) {
		pre {
			font-size: 0.71875rem;
		}
		.screen {
			padding-inline: 1rem;
		}
	}
	.request {
		min-height: 4.5rem;
		padding: 0.625rem 0.75rem;
		border-radius: 0.625rem;
		background: oklch(1 0 0 / 0.04);
		box-shadow: inset 0 0 0 1px var(--c-line);
	}
	.response {
		min-height: 9rem;
	}
	.line {
		display: block;
		animation: stream 380ms cubic-bezier(0.2, 0.7, 0.2, 1) both;
	}
	@keyframes stream {
		from {
			opacity: 0;
			transform: translateY(5px);
			filter: blur(3px);
		}
	}
	.m {
		color: var(--c-soft);
	}
	.p {
		color: var(--c-path);
		font-weight: 500;
	}
	.c {
		color: var(--c-text);
	}
	.k {
		color: var(--c-key);
	}
	.s {
		color: var(--c-str);
	}
	.n {
		color: var(--c-num);
	}
	.caret {
		color: var(--c-str);
		animation: blink 0.9s steps(1) infinite;
	}
	.caret.hidden {
		display: none;
	}
	@keyframes blink {
		50% {
			opacity: 0;
		}
	}

	.foot {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
		padding: 0.625rem 0.875rem;
		border-top: 1px solid var(--c-line);
	}
	.calls {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
	}
	.calls button,
	.play {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.25rem 0.625rem 0.25rem 0.375rem;
		border-radius: 999px;
		font-size: 0.75rem;
		color: var(--c-soft);
		cursor: pointer;
		transition:
			background-color 250ms,
			color 250ms;
	}
	.calls button:hover,
	.play:hover {
		color: var(--c-text);
	}
	.calls button[aria-current='step'] {
		background: oklch(1 0 0 / 0.08);
		color: var(--c-text);
	}
	.calls .n {
		display: grid;
		place-items: center;
		width: 1.125rem;
		height: 1.125rem;
		border-radius: 50%;
		background: oklch(1 0 0 / 0.08);
		font-size: 0.625rem;
		color: inherit;
	}
	.calls button[aria-current='step'] .n {
		background: var(--c-str);
		color: oklch(0.2 0.03 268);
	}
	.play {
		margin-left: auto;
		padding-left: 0.5rem;
		box-shadow: inset 0 0 0 1px var(--c-line);
	}
	.play :global(svg) {
		width: 0.75rem;
		height: 0.75rem;
	}
	.console :global(button:focus-visible) {
		outline: 2px solid var(--c-str);
		outline-offset: 2px;
	}

	.status {
		padding: 0.75rem 1.25rem;
		border-top: 1px solid var(--c-line);
		font-size: 0.75rem;
		color: var(--c-soft);
		opacity: 0.35;
		transition: opacity 400ms;
	}
	.status.shown {
		opacity: 1;
	}

	@media (prefers-reduced-motion: reduce) {
		.console:not([data-motion='allowed']) .line,
		.console:not([data-motion='allowed']) .caret {
			animation: none;
		}
	}
</style>
