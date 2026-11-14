<script lang="ts">
	import { resolve } from '$app/paths';
	import Roundel from '#lib/components/Roundel.svelte';
	import { Button } from '#lib/components/ui/button/index.js';
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import ScaleIcon from '@lucide/svelte/icons/scale';
	import ScrollTextIcon from '@lucide/svelte/icons/scroll-text';
	import UserCheckIcon from '@lucide/svelte/icons/user-check';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import HandIcon from '@lucide/svelte/icons/hand';
	import OctagonXIcon from '@lucide/svelte/icons/octagon-x';
	import PlugIcon from '@lucide/svelte/icons/plug';
	import BracesIcon from '@lucide/svelte/icons/braces';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';

	const principles = [
		{
			icon: UserCheckIcon,
			title: 'A person sets the mandate',
			text: 'Spend, assortment, required claims, excluded allergens, substitutes and delivery. The agent can read its mandate, never widen it.'
		},
		{
			icon: ScaleIcon,
			title: 'Code judges, not a model',
			text: 'Every quote and order gets one policy outcome with reason codes. Same input, same answer, so any decision can be replayed.'
		},
		{
			icon: ScrollTextIcon,
			title: 'Everything is written down',
			text: 'Every tool call, decision and approval goes into an append-only audit trail that both the buyer and Valio Aimo can read.'
		}
	];

	const steps = [
		{
			n: 'I',
			title: 'The request',
			text: 'The buyer tells their agent what the kitchen needs, in their own words. The agent works out what “by Monday” means and says so.',
			artefact: '“1,000 litres of lactose-free milk by Monday”'
		},
		{
			n: 'II',
			title: 'The search',
			text: 'The agent searches Valio Aimo’s catalogue by what a product declares, not by what its name suggests. Unknown never counts as free-from.',
			artefact: 'claim FREE_FROM_LACTOSE'
		},
		{
			n: 'III',
			title: 'The offer',
			text: 'Live price and stock are fetched for a shortlist only. Each figure says where it came from and how long it holds.',
			artefact: '€1.84 per litre, 64 cases in stock'
		},
		{
			n: 'IV',
			title: 'The quote',
			text: 'Saint Elmo turns litres into the cases Valio Aimo sells, rounds to the lot size and shows its working on every line.',
			artefact: '1,000 L → 50 KI, 1 KI ≈ 20 L'
		},
		{
			n: 'V',
			title: 'The judgement',
			text: 'Plain code, not a language model, checks the quote against the mandate. The answer is one of three, always with a reason.',
			artefact: 'OVER_AUTO_APPROVE_LIMIT'
		},
		{
			n: 'VI',
			title: 'The order',
			text: 'A person signs off on their own screen, never through the agent. Price and stock are checked again at the moment of commitment.',
			artefact: 'PENDING_APPROVAL → PLACED'
		}
	];

	const outcomes = [
		{
			code: 'AUTO_APPROVE',
			tone: 'ok',
			icon: CircleCheckIcon,
			title: 'The agent decides alone',
			text: 'Orders within the spend it was given, for products that meet every requirement, delivered on time.'
		},
		{
			code: 'NEEDS_HUMAN',
			tone: 'hold',
			icon: HandIcon,
			title: 'A person decides',
			text: 'Orders over the auto-approve limit, substitutes the mandate asks to see, late deliveries, partial stock, products missing a required claim.'
		},
		{
			code: 'REJECT',
			tone: 'stop',
			icon: OctagonXIcon,
			title: 'Nobody can order it',
			text: 'A declared allergen the kitchen excludes, a blocked category, a passed closing time, or a total over the hard limit.'
		}
	] as const;

	const doors = [
		{
			icon: PlugIcon,
			title: 'MCP for agents',
			text: 'Any MCP client, such as Claude Desktop or Claude Code, connects with an Agent token and gets the same tools: search, offers, quotes, orders, status.'
		},
		{
			icon: BracesIcon,
			title: 'REST for everything else',
			text: 'The same API, described in OpenAPI 3.1. Responses follow JSON Schema, with GS1 codes for allergens, claims and packaging.'
		},
		{
			icon: KeyRoundIcon,
			title: 'Agent tokens',
			text: 'Signed, expiring and scoped. A token names its mandate but never carries it, and a buyer admin can revoke it from the next request on.'
		}
	];

	/**
	 * Fades a section up as it scrolls into view. Only content below the fold is
	 * hidden first, so the page reads fully without JavaScript or motion.
	 */
	function reveal(node: HTMLElement) {
		if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
		if (node.getBoundingClientRect().top < innerHeight) return;
		node.classList.add('reveal');
		const io = new IntersectionObserver(
			(entries) => {
				for (const e of entries) {
					if (e.isIntersecting) {
						node.classList.add('is-in');
						io.disconnect();
					}
				}
			},
			{ rootMargin: '0px 0px -12% 0px' }
		);
		io.observe(node);
		return () => io.disconnect();
	}
</script>

<svelte:head>
	<title>Saint Elmo</title>
	<meta
		name="description"
		content="Autonomous procurement for hotels, restaurants and professional kitchens: purchasing agents order from Valio Aimo within the mandate you set, with every decision on the record."
	/>
	<link rel="preload" as="image" href="/art/erasmus-plate-900.webp" />
</svelte:head>

<div class="page">
	<a href="#main" class="skip">Skip to content</a>

	<header class="nav">
		<div class="wrap nav-inner">
			<a href={resolve('/(marketing)')} class="brand" aria-label="Saint Elmo, home">
				<Roundel size={34} />
				<span>Saint Elmo</span>
			</a>
			<nav aria-label="Site" class="nav-links">
				<a href="#how">How it works</a>
				<a href="#mandate">Mandates</a>
				<a href="#open">Developers</a>
			</nav>
			<div class="nav-actions">
				<a href={resolve('login')} class="nav-signin">Sign in</a>
				<Button
					href={resolve('login')}
					class="hidden h-9 rounded-full bg-lapis-night px-4 text-vellum hover:bg-lapis-deep sm:inline-flex"
				>
					Open the console
				</Button>
			</div>
		</div>
	</header>

	<main id="main">
		<!-- Hero: ivory paper, the panel in an altar-arch, and the console's own answers laid over it. -->
		<section class="hero" aria-labelledby="hero-title">
			<div class="glow" aria-hidden="true"></div>
			<div class="wrap hero-grid">
				<div class="hero-text">
					<p class="eyebrow">
						<span class="eyebrow-dot" aria-hidden="true"></span>
						Hotels · Restaurants · Professional kitchens
					</p>
					<h1 id="hero-title" class="font-display-tight">
						A watch kept over every agent that <em>buys you time</em>
					</h1>
					<p class="lede">
						Your agents order from Valio Aimo on their own, inside the limits you set. Anything
						beyond them waits for you.
					</p>
					<div class="ctas">
						<Button
							href={resolve('login')}
							size="lg"
							class="h-12 rounded-full bg-lapis-night px-6 text-base text-vellum shadow-[0_14px_30px_-14px] shadow-lapis-night/60 hover:bg-lapis-deep"
						>
							Open the console <ArrowRightIcon />
						</Button>
						<a href="#how" class="cta-ghost">See an order from start to finish</a>
					</div>
					<div class="partner">
						<span>Ordering from</span>
						<img src="/brand/valio-aimo-wordmark.png" alt="Valio Aimo" width="340" height="140" />
					</div>
				</div>

				<figure class="hero-figure">
					<div class="arch">
						<img
							src="/art/erasmus-plate-900.webp"
							srcset="/art/erasmus-plate-900.webp 900w, /art/erasmus-plate-1600.webp 1600w, /art/erasmus-plate-2379.webp 2379w"
							sizes="(min-width: 1024px) 30rem, 92vw"
							width="2379"
							height="3060"
							alt="Saint Erasmus in a jewelled mitre and gold vestments, holding a crozier, meeting Saint Maurice in armour."
							fetchpriority="high"
						/>
						<span class="corona" aria-hidden="true"></span>
					</div>

					<!-- What the console shows for this kind of order: a policy outcome and the mandate it was judged by. -->
					<div class="float float-outcome" aria-hidden="true">
						<p class="float-head">
							<span class="code">place_order</span>
							<span class="float-agent code">dairy-restock</span>
						</p>
						<p class="float-status"><span class="dot dot-hold"></span>Needs approval</p>
						<p class="float-reason code">OVER_AUTO_APPROVE_LIMIT</p>
						<p class="float-meta tabular">€1,840 &gt; €1,500 auto-approve</p>
					</div>
					<div class="float float-mandate" aria-hidden="true">
						<p class="float-title">Mandate <span class="code">dairy-restock</span></p>
						<dl>
							<div>
								<dt>Decides alone up to</dt>
								<dd class="tabular">€1,500</dd>
							</div>
							<div>
								<dt>Order limit</dt>
								<dd class="tabular">€2,000</dd>
							</div>
							<div>
								<dt>Requires</dt>
								<dd class="code">FREE_FROM_LACTOSE</dd>
							</div>
						</dl>
					</div>

					<figcaption>
						Saint Erasmus, called Saint Elmo, from Matthias Grünewald’s <cite
							>The Meeting of Saint Erasmus and Saint Maurice</cite
						>, c. 1520–24. Sailors who saw blue fire on their masts in a storm took it as his sign
						that the ship was being watched over.
					</figcaption>
				</figure>
			</div>
		</section>

		<!-- Principles -->
		<section class="vellum principles" aria-label="Principles">
			<div class="wrap">
				<ul class="principle-grid" {@attach reveal}>
					{#each principles as p (p.title)}
						<li>
							<span class="principle-icon"><p.icon aria-hidden="true" /></span>
							<h2>{p.title}</h2>
							<p>{p.text}</p>
						</li>
					{/each}
				</ul>
			</div>
		</section>

		<!-- How one order travels -->
		<section id="how" class="vellum how" aria-labelledby="how-title">
			<div class="wrap">
				<div class="section-head" {@attach reveal}>
					<p class="kicker">How it works</p>
					<h2 id="how-title" class="font-display-tight">How one order travels</h2>
					<p class="section-intro">
						Every order an agent places goes through the same six steps. The agent proposes, and
						Saint Elmo checks, converts and records. Choosing is the agent’s job; enforcing the
						limits never is.
					</p>
				</div>
				<ol class="steps" {@attach reveal}>
					{#each steps as s (s.n)}
						<li>
							<span class="numeral" aria-hidden="true">{s.n}</span>
							<h3>{s.title}</h3>
							<p>{s.text}</p>
							<p class="artefact code">{s.artefact}</p>
						</li>
					{/each}
				</ol>
			</div>
		</section>

		<!-- Mandate and policy outcomes -->
		<section id="mandate" class="night mandate" aria-labelledby="mandate-title">
			<div class="wrap mandate-grid">
				<figure class="side-figure" {@attach reveal}>
					<div class="arch arch-soft">
						<img
							src="/art/trh-septembre.webp"
							width="1159"
							height="1922"
							loading="lazy"
							alt="The grape harvest beneath the Château de Saumur, with a zodiac calendar arched across a deep blue sky."
						/>
					</div>
					<figcaption>
						September, from the <cite>Très Riches Heures du Duc de Berry</cite>, Limbourg brothers,
						c. 1412–16.
					</figcaption>
				</figure>

				<div class="mandate-text">
					<div {@attach reveal}>
						<p class="kicker kicker-gold">Mandates and policy</p>
						<h2 id="mandate-title" class="font-display-tight">
							What an agent may do alone, and what waits for a person
						</h2>
						<p class="body">
							A buyer admin writes each agent’s mandate once: what it may spend, what it may buy,
							which claims and allergens matter, and how it may substitute. The agent can read its
							mandate. It can never change it, and nothing it writes can talk its way past it.
						</p>
					</div>

					<ul class="outcomes" {@attach reveal}>
						{#each outcomes as o (o.code)}
							<li class="outcome outcome-{o.tone}">
								<span class="outcome-icon"><o.icon aria-hidden="true" /></span>
								<div>
									<p class="outcome-code code">{o.code}</p>
									<h3>{o.title}</h3>
									<p>{o.text}</p>
								</div>
							</li>
						{/each}
					</ul>

					<p class="body fine" {@attach reveal}>
						Every figure an agent is shown carries its provenance. Stock from Valio Aimo’s own
						warehouse is a real count; stock shipped by a supplier is marked unknown. Allergens come
						from the manufacturer or are marked missing. Carbon figures are labelled as
						product-group averages.
					</p>
				</div>
			</div>
		</section>

		<!-- Openness -->
		<section id="open" class="deep open" aria-labelledby="open-title">
			<div class="wrap open-grid">
				<div {@attach reveal}>
					<p class="kicker kicker-gold">For developers</p>
					<h2 id="open-title" class="font-display-tight">One API, two doors</h2>
					<p class="body">
						The MCP server is a thin adapter over the same backend that REST clients and the console
						call, so every rule is checked in exactly one place.
					</p>
					<ul class="doors">
						{#each doors as d (d.title)}
							<li>
								<span class="door-icon"><d.icon aria-hidden="true" /></span>
								<div>
									<h3>{d.title}</h3>
									<p>{d.text}</p>
								</div>
							</li>
						{/each}
					</ul>
				</div>

				<figure class="terminal" {@attach reveal}>
					<div class="terminal-bar">
						<span class="lights" aria-hidden="true"><i></i><i></i><i></i></span>
						<span class="code">place_order · dairy-restock</span>
					</div>
					<pre class="code"><code
							><span class="t-key">"status"</span>: <span class="t-str">"PENDING_APPROVAL"</span>,
<span class="t-key">"policy"</span>: &#123;
  <span class="t-key">"outcome"</span>: <span class="t-str">"NEEDS_HUMAN"</span>,
  <span class="t-key">"reasonCodes"</span>: [<span class="t-str">"OVER_AUTO_APPROVE_LIMIT"</span>]
&#125;,
<span class="t-key">"total"</span>: &#123; <span class="t-key">"net"</span>: <span class="t-num"
								>1840.00</span
							>, <span class="t-key">"currency"</span>: <span class="t-str">"EUR"</span
							> &#125;</code
						></pre>
					<figcaption>
						Illustrative. The agent never waits for a person: it checks back with
						<span class="code">get_order_status</span>.
					</figcaption>
				</figure>
			</div>
		</section>

		<!-- Closing call to action -->
		<section class="vellum cta-band" aria-labelledby="cta-title">
			<div class="wrap cta-inner" {@attach reveal}>
				<Roundel size={64} />
				<h2 id="cta-title" class="font-display-tight">
					Let agents do the ordering. <em>Keep the deciding.</em>
				</h2>
				<Button
					href={resolve('login')}
					size="lg"
					class="h-12 rounded-full bg-lapis-night px-6 text-base text-vellum hover:bg-lapis"
				>
					Open the console <ArrowRightIcon />
				</Button>
			</div>
		</section>
	</main>

	<footer class="night colophon" aria-labelledby="colophon-title">
		<div class="wrap">
			<div class="colophon-top">
				<a href={resolve('/(marketing)')} class="brand">
					<Roundel size={28} />
					<span>Saint Elmo</span>
				</a>
				<img
					src="/brand/valio-aimo-wordmark.png"
					alt="Valio Aimo"
					width="340"
					height="140"
					class="colophon-mark"
				/>
			</div>
			<h2 id="colophon-title" class="sr-only">Colophon</h2>
			<div class="colophon-grid">
				<p>
					Made for the Valio Aimo challenge at Junction 2026. Every product, price and order shown
					here is synthetic.
				</p>
				<p>
					Agents connect over MCP or plain REST described in OpenAPI 3.1. Responses follow JSON
					Schema, with GS1 codes for allergens, claims and packaging.
				</p>
				<p>
					Paintings from Wikimedia Commons, in the public domain: Grünewald, Alte Pinakothek,
					Munich; the Limbourg brothers, Musée Condé, Chantilly.
				</p>
			</div>
		</div>
	</footer>
</div>

<style>
	/*
	 * A fixed palette, independent of the console's light/dark mode: an ivory hero
	 * and vellum leaves in ink, alternating with night-lapis sections in gold and vellum.
	 */
	.page {
		--ink: oklch(0.24 0.03 60);
		--ink-soft: oklch(0.42 0.03 60);
		--on-night: oklch(0.94 0.02 85);
		--on-night-soft: oklch(0.94 0.02 85 / 0.72);
		--hair: oklch(0.73 0.11 82 / 0.35);
		--ok-tone: oklch(0.74 0.12 158);
		--hold-tone: oklch(0.8 0.12 80);
		--stop-tone: oklch(0.7 0.16 32);
		--gold-fixed: oklch(0.76 0.11 82);
		/* The bright half: ivory paper, ink type, an ochre gold that holds contrast on light. */
		--ivory: oklch(0.985 0.008 85);
		--ivory-deep: oklch(0.965 0.016 85);
		--ochre: oklch(0.55 0.11 68);
		--ink-faint: oklch(0.24 0.03 60 / 0.1);

		/* Ivory under the sticky nav; every section paints its own background. */
		background: var(--ivory);
		color: var(--on-night);
		font-family: var(--font-sans);
		overflow-x: clip;
	}

	.wrap {
		width: min(76rem, 100% - 2.5rem);
		margin-inline: auto;
	}
	@media (min-width: 640px) {
		.wrap {
			width: min(76rem, 100% - 4rem);
		}
	}

	a {
		color: inherit;
	}
	.page :global(a:focus-visible) {
		outline: 2px solid var(--gold-fixed);
		outline-offset: 3px;
		border-radius: 4px;
	}

	.skip {
		position: absolute;
		left: 1rem;
		top: -3rem;
		z-index: 50;
		padding: 0.5rem 0.875rem;
		border-radius: 999px;
		background: var(--vellum);
		color: var(--lapis-night);
		font-size: 0.875rem;
	}
	.skip:focus {
		top: 1rem;
	}

	em {
		font-style: italic;
		color: var(--gold-fixed);
	}
	.hero em {
		color: var(--ochre);
	}

	/* Nav: glass over the night sky */
	.nav {
		position: sticky;
		top: 0;
		z-index: 40;
		background: oklch(0.985 0.008 85 / 0.78);
		backdrop-filter: blur(14px) saturate(1.4);
		-webkit-backdrop-filter: blur(14px) saturate(1.4);
		border-bottom: 1px solid var(--ink-faint);
		color: var(--ink);
	}
	.nav-inner {
		display: flex;
		align-items: center;
		gap: 1.5rem;
		height: 4rem;
	}
	.brand {
		display: inline-flex;
		align-items: center;
		gap: 0.625rem;
		font-family: var(--font-display);
		font-size: 1.375rem;
		font-weight: 500;
		letter-spacing: -0.01em;
		text-decoration: none;
		white-space: nowrap;
	}
	.nav-links {
		display: none;
		gap: 1.75rem;
		margin-left: 1.5rem;
		font-size: 0.875rem;
	}
	@media (min-width: 820px) {
		.nav-links {
			display: flex;
		}
	}
	.nav-links a,
	.nav-signin {
		color: var(--ink-soft);
		text-decoration: none;
		transition: color 150ms;
	}
	.nav-links a:hover,
	.nav-signin:hover {
		color: var(--ink);
	}
	.nav-actions {
		display: flex;
		align-items: center;
		gap: 1.25rem;
		margin-left: auto;
		font-size: 0.875rem;
	}

	/* Hero */
	.hero {
		position: relative;
		isolation: isolate;
		padding-block: 3.5rem 5rem;
		background: linear-gradient(180deg, var(--ivory) 0%, var(--ivory) 55%, var(--ivory-deep) 100%);
		color: var(--ink);
		border-bottom: 1px solid var(--ink-faint);
	}
	@media (min-width: 1024px) {
		.hero {
			padding-block: 5rem 7.5rem;
		}
	}
	/* Gold leaf as ambient light behind the panel, plus a faint paper grain. */
	.glow {
		position: absolute;
		inset: 0;
		z-index: -1;
		background:
			radial-gradient(ellipse 42% 55% at 74% 42%, oklch(0.86 0.09 82 / 0.35), transparent 70%),
			radial-gradient(ellipse 30% 30% at 76% 14%, oklch(0.85 0.06 268 / 0.25), transparent 70%),
			url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.05'/%3E%3C/svg%3E");
	}
	.hero-grid {
		display: grid;
		gap: 4rem;
		align-items: center;
	}
	@media (min-width: 1024px) {
		.hero-grid {
			grid-template-columns: minmax(0, 1fr) 30rem;
			gap: 5rem;
		}
	}
	.hero-text > * {
		animation: rise 900ms cubic-bezier(0.2, 0.7, 0.2, 1) both;
	}
	.hero-text > :nth-child(2) {
		animation-delay: 80ms;
	}
	.hero-text > :nth-child(3) {
		animation-delay: 160ms;
	}
	.hero-text > :nth-child(4) {
		animation-delay: 240ms;
	}
	.hero-text > :nth-child(5) {
		animation-delay: 320ms;
	}

	.eyebrow {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.375rem 0.875rem 0.375rem 0.625rem;
		border: 1px solid oklch(0.73 0.11 82 / 0.45);
		border-radius: 999px;
		background: oklch(1 0 0 / 0.7);
		font-size: 0.8125rem;
		color: var(--ink-soft);
	}
	.eyebrow-dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: var(--gold-fixed);
		box-shadow: 0 0 0 4px oklch(0.76 0.11 82 / 0.22);
	}
	h1 {
		margin-top: 1.5rem;
		max-width: 14ch;
		font-size: clamp(3rem, 7vw, 5.75rem);
		line-height: 0.98;
		text-wrap: balance;
		color: var(--ink);
	}
	.lede {
		margin-top: 1.75rem;
		max-width: 36rem;
		font-size: 1.125rem;
		line-height: 1.65;
		color: var(--ink-soft);
	}
	@media (min-width: 640px) {
		.lede {
			font-size: 1.1875rem;
		}
	}
	.ctas {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.75rem 1.5rem;
		margin-top: 2.5rem;
	}
	.cta-ghost {
		font-size: 0.9375rem;
		color: var(--ink);
		text-decoration: underline;
		text-decoration-color: oklch(0.55 0.11 68 / 0.4);
		text-underline-offset: 6px;
		transition: text-decoration-color 150ms;
	}
	.cta-ghost:hover {
		text-decoration-color: var(--ochre);
	}
	.partner {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		margin-top: 3.5rem;
		font-size: 0.8125rem;
		color: var(--ink-soft);
	}
	.partner img {
		height: 2.25rem;
		width: auto;
		border-radius: 4px;
	}

	/* The painting, in an altar-panel arch with a single gold hairline. */
	.hero-figure {
		position: relative;
		max-width: 30rem;
		margin-inline: auto;
		animation: rise 1100ms cubic-bezier(0.2, 0.7, 0.2, 1) 120ms both;
	}
	.arch {
		position: relative;
		border-radius: 50% 50% 1.25rem 1.25rem / 12% 12% 1.25rem 1.25rem;
		overflow: hidden;
		box-shadow:
			0 0 0 1px oklch(0.73 0.11 82 / 0.8),
			0 0 0 9px var(--ivory),
			0 0 0 10px oklch(0.73 0.11 82 / 0.45),
			0 50px 80px -40px oklch(0.35 0.06 60 / 0.45);
	}
	.arch img {
		display: block;
		width: 100%;
		height: auto;
	}
	.arch-soft {
		border-radius: 50% 50% 1rem 1rem / 9% 9% 1rem 1rem;
	}
	/* Saint Elmo's fire at the tip of the crozier, kindled once on load. */
	.corona {
		position: absolute;
		left: 42.8%;
		top: 9.1%;
		width: 20%;
		aspect-ratio: 1;
		translate: -50% -50%;
		border-radius: 50%;
		background: radial-gradient(
			circle,
			oklch(0.92 0.05 268 / 0.85) 0%,
			oklch(0.78 0.11 268 / 0.6) 22%,
			oklch(0.78 0.11 268 / 0.18) 48%,
			transparent 70%
		);
		mix-blend-mode: screen;
		pointer-events: none;
		opacity: 0.45;
		animation: kindle 3.2s ease-out 0.9s both;
	}
	figcaption {
		margin-top: 1.25rem;
		font-size: 0.8125rem;
		line-height: 1.55;
		color: var(--ink-soft);
	}
	figcaption cite {
		font-family: var(--font-display);
		font-style: italic;
		font-size: 1.0625em;
	}

	/* Console fragments floating over the panel: the modern half of the picture. */
	.float {
		position: absolute;
		z-index: 2;
		border-radius: 0.875rem;
		font-size: 0.8125rem;
		line-height: 1.35;
		box-shadow: 0 24px 50px -24px oklch(0.3 0.05 60 / 0.5);
		animation:
			rise 900ms cubic-bezier(0.2, 0.7, 0.2, 1) both,
			bob 7s ease-in-out 1.2s infinite;
	}
	.float-outcome {
		top: 22%;
		right: -1rem;
		width: 15.5rem;
		padding: 0.875rem 1rem;
		background: oklch(0.2 0.04 268 / 0.78);
		border: 1px solid oklch(1 0 0 / 0.12);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		color: var(--on-night);
		animation-delay: 500ms, 1.4s;
	}
	.float-mandate {
		bottom: 18%;
		left: -1rem;
		width: 15rem;
		padding: 0.875rem 1rem;
		background: oklch(0.97 0.015 85);
		color: var(--ink);
		border: 1px solid oklch(0.73 0.11 82 / 0.5);
		animation-delay: 700ms, 2.6s;
	}
	@media (min-width: 1024px) {
		.float-outcome {
			right: -1.25rem;
		}
		.float-mandate {
			left: -2.5rem;
		}
	}
	@media (min-width: 1280px) {
		.float-outcome {
			right: -3.5rem;
		}
		.float-mandate {
			left: -4rem;
		}
	}
	@media (max-width: 479px) {
		.float {
			display: none;
		}
	}
	.float-head {
		display: flex;
		justify-content: space-between;
		gap: 0.5rem;
		color: var(--on-night-soft);
		font-size: 0.75rem;
	}
	.float-agent {
		color: var(--corona);
	}
	.float-status {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-top: 0.625rem;
		font-weight: 600;
		font-size: 0.9375rem;
	}
	.dot {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
	}
	.dot-hold {
		background: var(--hold-tone);
		box-shadow: 0 0 0 3px oklch(0.8 0.12 80 / 0.2);
	}
	.float-reason {
		display: inline-block;
		margin-top: 0.5rem;
		padding: 0.125rem 0.5rem;
		border-radius: 0.375rem;
		background: oklch(0.8 0.12 80 / 0.14);
		color: var(--hold-tone);
		font-size: 0.6875rem;
	}
	.float-meta {
		margin-top: 0.375rem;
		color: var(--on-night-soft);
		font-size: 0.75rem;
	}
	.float-title {
		font-weight: 600;
		font-size: 0.8125rem;
	}
	.float-title .code {
		color: var(--ink-soft);
		font-weight: 400;
	}
	.float-mandate dl {
		margin-top: 0.5rem;
	}
	.float-mandate dl div {
		display: flex;
		justify-content: space-between;
		gap: 0.75rem;
		padding-block: 0.3rem;
		border-top: 1px solid oklch(0.24 0.03 60 / 0.1);
		font-size: 0.75rem;
	}
	.float-mandate dt {
		color: var(--ink-soft);
	}
	.float-mandate dd {
		font-weight: 600;
	}
	.float-mandate dd.code {
		font-weight: 500;
		font-size: 0.6875rem;
	}

	/* Vellum leaves */
	.vellum {
		background: var(--vellum);
		color: var(--ink);
	}
	.principles {
		padding-block: 4rem;
		border-bottom: 1px solid oklch(0.24 0.03 60 / 0.1);
	}
	.principle-grid {
		display: grid;
		gap: 2.5rem;
	}
	@media (min-width: 768px) {
		.principle-grid {
			grid-template-columns: repeat(3, 1fr);
			gap: 3rem;
		}
	}
	.principle-icon {
		display: grid;
		place-items: center;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 0.75rem;
		background: var(--lapis-night);
		color: var(--gold-fixed);
	}
	.principle-icon :global(svg) {
		width: 1.125rem;
		height: 1.125rem;
	}
	.principles h2 {
		margin-top: 1rem;
		font-family: var(--font-display);
		font-size: 1.5rem;
		font-weight: 500;
		letter-spacing: -0.015em;
		line-height: 1.15;
	}
	.principles p {
		margin-top: 0.5rem;
		font-size: 0.9375rem;
		line-height: 1.6;
		color: var(--ink-soft);
	}

	.how {
		padding-block: 5.5rem 6.5rem;
		scroll-margin-top: 4rem;
	}
	.section-head {
		display: grid;
		gap: 1rem 4rem;
		align-items: end;
	}
	@media (min-width: 900px) {
		.section-head {
			grid-template-columns: auto minmax(0, 30rem);
			justify-content: space-between;
		}
		.section-head .kicker {
			grid-column: 1 / -1;
		}
	}
	.kicker {
		font-size: 0.75rem;
		font-weight: 600;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--vermilion);
	}
	.kicker-gold {
		color: var(--gold-fixed);
	}
	.how h2,
	.mandate h2,
	.open h2 {
		font-size: clamp(2.5rem, 5vw, 4rem);
		text-wrap: balance;
	}
	.section-intro {
		font-size: 1.0625rem;
		line-height: 1.65;
		color: var(--ink-soft);
	}
	.steps {
		display: grid;
		gap: 1rem;
		margin-top: 3.5rem;
		counter-reset: step;
	}
	@media (min-width: 720px) {
		.steps {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	@media (min-width: 1100px) {
		.steps {
			grid-template-columns: repeat(3, 1fr);
		}
	}
	.steps li {
		position: relative;
		padding: 1.75rem 1.5rem 1.5rem;
		border-radius: 1.125rem;
		background: oklch(0.985 0.01 85);
		border: 1px solid oklch(0.24 0.03 60 / 0.09);
		box-shadow: 0 1px 0 oklch(1 0 0 / 0.8) inset;
		transition:
			transform 250ms cubic-bezier(0.2, 0.7, 0.2, 1),
			box-shadow 250ms;
	}
	.steps li:hover {
		transform: translateY(-3px);
		box-shadow: 0 20px 40px -24px oklch(0.24 0.03 60 / 0.35);
	}
	.numeral {
		display: block;
		font-family: var(--font-display);
		font-style: italic;
		font-size: 2.25rem;
		line-height: 1;
		color: var(--vermilion);
	}
	.steps h3 {
		margin-top: 0.875rem;
		font-size: 1.0625rem;
		font-weight: 600;
		letter-spacing: -0.01em;
	}
	.steps p {
		margin-top: 0.375rem;
		font-size: 0.9375rem;
		line-height: 1.6;
		color: var(--ink-soft);
	}
	.steps .artefact {
		display: inline-block;
		margin-top: 1rem;
		padding: 0.25rem 0.625rem;
		border-radius: 0.5rem;
		background: var(--lapis-night);
		color: var(--vellum);
		font-size: 0.75rem;
		line-height: 1.5;
	}

	/* Night and deep sections */
	.night {
		background: var(--lapis-night);
	}
	.deep {
		background:
			radial-gradient(ellipse 60% 70% at 85% 30%, oklch(0.78 0.11 268 / 0.12), transparent 70%),
			var(--lapis-deep);
	}
	.mandate {
		padding-block: 6.5rem;
		scroll-margin-top: 4rem;
	}
	.mandate-grid {
		display: grid;
		gap: 4rem;
	}
	@media (min-width: 1024px) {
		.mandate-grid {
			grid-template-columns: 20rem minmax(0, 1fr);
			gap: 6rem;
			align-items: start;
		}
		.side-figure {
			position: sticky;
			top: 6rem;
		}
	}
	.side-figure {
		max-width: 20rem;
	}
	.mandate h2,
	.open h2 {
		margin-top: 1rem;
		color: var(--on-night);
	}
	.body {
		margin-top: 1.5rem;
		max-width: 40rem;
		font-size: 1.0625rem;
		line-height: 1.7;
		color: var(--on-night-soft);
	}
	.fine {
		font-size: 0.9375rem;
	}
	.outcomes {
		display: grid;
		gap: 0.75rem;
		margin-top: 2.5rem;
	}
	.outcome {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 1rem;
		padding: 1.25rem 1.375rem;
		border-radius: 1rem;
		background: oklch(1 0 0 / 0.035);
		border: 1px solid oklch(1 0 0 / 0.08);
		border-left: 3px solid var(--tone);
	}
	.outcome-ok {
		--tone: var(--ok-tone);
	}
	.outcome-hold {
		--tone: var(--hold-tone);
	}
	.outcome-stop {
		--tone: var(--stop-tone);
	}
	.outcome-icon {
		display: grid;
		place-items: center;
		width: 2.25rem;
		height: 2.25rem;
		border-radius: 50%;
		background: color-mix(in oklch, var(--tone) 16%, transparent);
		color: var(--tone);
	}
	.outcome-icon :global(svg) {
		width: 1.125rem;
		height: 1.125rem;
	}
	.outcome-code {
		font-size: 0.6875rem;
		color: var(--tone);
	}
	.outcome h3 {
		margin-top: 0.125rem;
		font-size: 1.0625rem;
		font-weight: 600;
	}
	.outcome p:last-child {
		margin-top: 0.25rem;
		font-size: 0.9375rem;
		line-height: 1.6;
		color: var(--on-night-soft);
	}

	/* Developers */
	.open {
		padding-block: 6.5rem;
		scroll-margin-top: 4rem;
	}
	.open-grid {
		display: grid;
		gap: 4rem;
		align-items: center;
	}
	@media (min-width: 1024px) {
		.open-grid {
			grid-template-columns: minmax(0, 1fr) minmax(0, 32rem);
			gap: 5rem;
		}
	}
	.doors {
		display: grid;
		gap: 1.5rem;
		margin-top: 2.25rem;
	}
	.doors li {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 1rem;
	}
	.door-icon {
		display: grid;
		place-items: center;
		width: 2.25rem;
		height: 2.25rem;
		border-radius: 0.625rem;
		border: 1px solid var(--hair);
		color: var(--gold-fixed);
	}
	.door-icon :global(svg) {
		width: 1rem;
		height: 1rem;
	}
	.doors h3 {
		font-size: 1rem;
		font-weight: 600;
	}
	.doors p {
		margin-top: 0.25rem;
		font-size: 0.9375rem;
		line-height: 1.6;
		color: var(--on-night-soft);
	}
	.terminal {
		border-radius: 1rem;
		overflow: hidden;
		background: oklch(0.13 0.03 270);
		border: 1px solid oklch(1 0 0 / 0.1);
		box-shadow: 0 40px 80px -40px oklch(0 0 0 / 0.8);
	}
	.terminal-bar {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid oklch(1 0 0 / 0.08);
		font-size: 0.75rem;
		color: var(--on-night-soft);
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
	.terminal pre {
		margin: 0;
		padding: 1.25rem 1.25rem 1.5rem;
		overflow-x: auto;
		font-size: 0.8125rem;
		line-height: 1.7;
		color: var(--on-night);
	}
	.t-key {
		color: var(--corona);
	}
	.t-str {
		color: var(--gold-fixed);
	}
	.t-num {
		color: var(--ok-tone);
	}
	.terminal figcaption {
		margin: 0;
		padding: 0.875rem 1.25rem;
		border-top: 1px solid oklch(1 0 0 / 0.08);
		font-size: 0.75rem;
	}

	/* Closing band */
	.cta-band {
		padding-block: 6rem;
	}
	.cta-inner {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2rem;
		text-align: center;
	}
	.cta-band h2 {
		font-size: clamp(2.25rem, 5vw, 3.75rem);
		text-wrap: balance;
	}
	.cta-band em {
		display: block;
		color: var(--vermilion);
	}

	/* Colophon */
	.colophon {
		padding-block: 3.5rem 4rem;
		border-top: 1px solid var(--hair);
	}
	.colophon-top {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: 1.5rem;
	}
	.colophon .brand {
		font-size: 1.125rem;
	}
	.colophon-mark {
		height: 2.25rem;
		width: auto;
		border-radius: 4px;
	}
	.colophon-grid {
		display: grid;
		gap: 1rem 3rem;
		margin-top: 2rem;
		padding-top: 2rem;
		border-top: 1px solid oklch(1 0 0 / 0.08);
		font-size: 0.8125rem;
		line-height: 1.65;
		color: var(--on-night-soft);
	}
	@media (min-width: 768px) {
		.colophon-grid {
			grid-template-columns: repeat(3, 1fr);
		}
	}

	/* Motion */
	.page :global(.reveal) {
		opacity: 0;
		transform: translateY(24px);
		transition:
			opacity 800ms cubic-bezier(0.2, 0.7, 0.2, 1),
			transform 800ms cubic-bezier(0.2, 0.7, 0.2, 1);
	}
	.page :global(.reveal.is-in) {
		opacity: 1;
		transform: none;
	}
	@keyframes rise {
		from {
			opacity: 0;
			transform: translateY(18px);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes bob {
		0%,
		100% {
			translate: 0 0;
		}
		50% {
			translate: 0 -6px;
		}
	}
	@keyframes kindle {
		0% {
			opacity: 0;
			scale: 0.4;
		}
		18% {
			opacity: 0.95;
			scale: 1.08;
		}
		26% {
			opacity: 0.55;
		}
		34% {
			opacity: 0.9;
		}
		100% {
			opacity: 0.45;
			scale: 1;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.hero-text > *,
		.hero-figure,
		.float,
		.corona {
			animation: none;
		}
		.steps li:hover {
			transform: none;
		}
	}
</style>
