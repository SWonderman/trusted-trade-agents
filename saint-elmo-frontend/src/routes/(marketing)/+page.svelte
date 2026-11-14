<script lang="ts">
	import { resolve } from '$app/paths';
	import Roundel from '#lib/components/Roundel.svelte';

	const folios = [
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
			text: 'A person signs off through their own screen, never through the agent. Price and stock are checked again at the moment of commitment.',
			artefact: 'PENDING_APPROVAL → PLACED'
		}
	];

	const tiers = [
		{
			title: 'The agent decides alone',
			text: 'Orders within the spend it was given, for products that meet every requirement, delivered on time.'
		},
		{
			title: 'A person decides',
			text: 'Orders over the auto-approve limit, substitutes the mandate asks to see, late deliveries, partial stock, products missing a required claim.'
		},
		{
			title: 'Nobody can order it',
			text: 'A declared allergen the kitchen excludes, a blocked category, a passed closing time, or a total over the hard limit.'
		}
	];
</script>

<svelte:head>
	<title>Saint Elmo</title>
	<meta
		name="description"
		content="The gateway that lets a kitchen’s purchasing agents order from Valio Aimo within limits a person sets, with every decision written down."
	/>
	<link rel="preload" as="image" href="/art/erasmus-plate-900.webp" />
</svelte:head>

<div class="folio">
	<header class="masthead">
		<a href={resolve('/(marketing)')} class="brand">
			<Roundel size={44} />
			<span>Saint Elmo</span>
		</a>
		<nav aria-label="Site">
			<a href="#folios" class="navlink">How it works</a>
			<a href={resolve('login')} class="navlink signin">Sign in</a>
		</nav>
	</header>

	<main>
		<section class="hero" aria-labelledby="hero-title">
			<div class="hero-text">
				<h1 id="hero-title">A watch kept over every agent that buys for your kitchen</h1>
				<p class="lede">
					Saint Elmo stands between your purchasing agents and Valio Aimo. Agents search, compare
					and order on their own, inside limits a person sets. Anything outside those limits waits
					for a human, and every step is written down.
				</p>
				<div class="ctas">
					<a href={resolve('login')} class="cta primary">Open the console</a>
					<a href="#folios" class="cta">See an order from start to finish</a>
				</div>
				<p class="partner">
					<span>Ordering from</span>
					<img src="/brand/valio-aimo-wordmark.png" alt="Valio Aimo" width="340" height="140" />
				</p>
			</div>

			<figure class="hero-plate">
				<div class="frame">
					<img
						src="/art/erasmus-plate-900.webp"
						srcset="/art/erasmus-plate-900.webp 900w, /art/erasmus-plate-1600.webp 1600w, /art/erasmus-plate-2379.webp 2379w"
						sizes="(min-width: 1024px) 34rem, 92vw"
						width="2379"
						height="3060"
						alt="Saint Erasmus in a jewelled mitre and gold vestments, holding a crozier and a windlass, meeting Saint Maurice in armour."
						fetchpriority="high"
					/>
					<span class="corona" aria-hidden="true"></span>
				</div>
				<figcaption>
					Saint Erasmus, called Saint Elmo, from Matthias Grünewald’s <cite
						>The Meeting of Saint Erasmus and Saint Maurice</cite
					>, c. 1520–24. Sailors who saw blue fire on their masts in a storm took it as his sign
					that the ship was being watched over.
				</figcaption>
			</figure>
		</section>

		<section id="folios" class="leaf" aria-labelledby="folios-title">
			<h2 id="folios-title">How one order travels</h2>
			<p class="leaf-intro">
				<span class="initial" aria-hidden="true">E</span><span class="sr-only">E</span>very order an
				agent places goes through the same six steps. The agent proposes, and Saint Elmo checks,
				converts and records. Choosing is the agent’s job; enforcing the limits never is.
			</p>
			<ol class="folios">
				{#each folios as f (f.n)}
					<li>
						<span class="numeral" aria-hidden="true">{f.n}</span>
						<h3>{f.title}</h3>
						<p>{f.text}</p>
						<p class="artefact">{f.artefact}</p>
					</li>
				{/each}
			</ol>
		</section>

		<section class="mandate" aria-labelledby="mandate-title">
			<figure class="side-plate">
				<div class="frame">
					<img
						src="/art/trh-septembre.webp"
						width="1159"
						height="1922"
						loading="lazy"
						alt="The grape harvest beneath the Château de Saumur, with a zodiac calendar arched across a deep blue sky."
					/>
				</div>
				<figcaption>
					September, from the <cite>Très Riches Heures du Duc de Berry</cite>, Limbourg brothers, c.
					1412–16.
				</figcaption>
			</figure>

			<div class="mandate-text">
				<h2 id="mandate-title">What an agent may do alone, and what waits for a person</h2>
				<p>
					A person in the kitchen writes each agent’s mandate once: what it may spend, what it may
					buy, which claims and allergens matter, and how it may substitute. The agent can read its
					mandate. It can never change it, and nothing it writes can talk its way past it.
				</p>
				<dl class="tiers">
					{#each tiers as t (t.title)}
						<div>
							<dt>{t.title}</dt>
							<dd>{t.text}</dd>
						</div>
					{/each}
				</dl>
				<p>
					Every figure an agent is shown carries its provenance. Stock from Valio Aimo’s own
					warehouse is a real count; stock shipped by a supplier is marked unknown. Allergens come
					from the manufacturer or are marked missing. Carbon figures are labelled as product-group
					averages.
				</p>
			</div>
		</section>
	</main>

	<footer class="colophon" aria-labelledby="colophon-title">
		<h2 id="colophon-title">Colophon</h2>
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
				Paintings from Wikimedia Commons, in the public domain: Grünewald, Alte Pinakothek, Munich;
				the Limbourg brothers, Musée Condé, Chantilly.
			</p>
		</div>
		<img
			src="/brand/valio-aimo-wordmark.png"
			alt="Valio Aimo"
			width="340"
			height="140"
			class="colophon-mark"
		/>
	</footer>
</div>

<style>
	.folio {
		--ink: #2a2118;
		--ink-soft: #5a4c3c;
		min-height: 100dvh;
		background:
			radial-gradient(ellipse 80% 50% at 70% 0%, rgb(255 255 255 / 0.06), transparent 60%),
			var(--se-folio-lapis);
		color: var(--se-vellum);
		font-family: var(--font-serif);
		font-size: 1.125rem;
		line-height: 1.6;
		/* The page border of a manuscript: a double gilt rule inset from the edge. */
		box-shadow:
			inset 0 0 0 10px var(--se-folio-lapis),
			inset 0 0 0 11px var(--se-gold),
			inset 0 0 0 15px var(--se-folio-lapis),
			inset 0 0 0 16px color-mix(in srgb, var(--se-gold) 55%, transparent);
	}

	.masthead,
	main,
	.colophon {
		width: min(76rem, 100% - 2.5rem);
		margin-inline: auto;
	}
	@media (min-width: 640px) {
		.masthead,
		main,
		.colophon {
			width: min(76rem, 100% - 5rem);
		}
	}

	a {
		color: inherit;
	}
	a:focus-visible {
		outline: 2px solid var(--se-gold);
		outline-offset: 3px;
	}

	/* Masthead */
	.masthead {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding-block: 2rem 1rem;
	}
	.brand {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 1.375rem;
		font-weight: 500;
		text-decoration: none;
		letter-spacing: 0.005em;
		white-space: nowrap;
	}
	@media (max-width: 479px) {
		.navlink:not(.signin) {
			display: none;
		}
	}
	nav {
		display: flex;
		gap: 1.5rem;
		align-items: center;
	}
	.navlink {
		font-size: 1rem;
		text-decoration: none;
		color: color-mix(in srgb, var(--se-vellum) 80%, transparent);
	}
	.navlink:hover {
		color: var(--se-vellum);
	}
	.signin {
		padding: 0.4rem 0.9rem;
		border: 1px solid color-mix(in srgb, var(--se-gold) 70%, transparent);
		border-radius: 2px;
		color: var(--se-vellum);
	}

	/* Hero */
	.hero {
		display: grid;
		gap: 3rem;
		align-items: center;
		padding-block: 2.5rem 5rem;
	}
	@media (min-width: 1024px) {
		.hero {
			grid-template-columns: 1fr 34rem;
			gap: 4.5rem;
			padding-block: 3rem 7rem;
		}
	}
	h1 {
		font-family: var(--font-blackletter);
		font-weight: 600;
		font-size: clamp(2.75rem, 6.2vw, 5.25rem);
		line-height: 0.98;
		letter-spacing: 0.005em;
		color: var(--se-vellum);
		max-width: 13ch;
		text-wrap: balance;
	}
	.lede {
		margin-top: 1.75rem;
		max-width: 34rem;
		font-size: 1.25rem;
		line-height: 1.6;
		color: color-mix(in srgb, var(--se-vellum) 86%, transparent);
	}
	.ctas {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 2.25rem;
	}
	.cta {
		display: inline-flex;
		align-items: center;
		min-height: 2.875rem;
		padding: 0 1.25rem;
		border: 1px solid color-mix(in srgb, var(--se-vellum) 45%, transparent);
		border-radius: 2px;
		font-size: 1.0625rem;
		text-decoration: none;
		transition:
			background-color 150ms,
			border-color 150ms;
	}
	.cta:hover {
		border-color: var(--se-vellum);
	}
	.cta.primary {
		background: var(--se-vellum);
		border-color: var(--se-gold);
		box-shadow:
			inset 0 0 0 2px var(--se-vellum),
			inset 0 0 0 3px var(--se-gold);
		color: var(--se-folio-deep);
		font-weight: 500;
	}
	.cta.primary:hover {
		background: #f7f0de;
	}
	.partner {
		display: flex;
		align-items: center;
		gap: 0.875rem;
		margin-top: 3rem;
		font-size: 0.9375rem;
		color: color-mix(in srgb, var(--se-vellum) 70%, transparent);
	}
	.partner img {
		height: 2.5rem;
		width: auto;
		border-radius: 3px;
	}

	/* Plates: paintings in a gilt frame */
	.frame {
		position: relative;
		padding: 10px;
		background: linear-gradient(145deg, #7d5f22, #e3c56f 30%, #a07a2c 55%, #f0d993 75%, #8a6a24);
		box-shadow:
			0 30px 60px -30px rgb(0 0 0 / 0.65),
			0 0 0 1px rgb(0 0 0 / 0.35);
	}
	.frame img {
		display: block;
		width: 100%;
		height: auto;
		box-shadow: inset 0 0 0 1px rgb(0 0 0 / 0.4);
		outline: 1px solid rgb(0 0 0 / 0.45);
	}
	figcaption {
		margin-top: 1rem;
		font-size: 0.9375rem;
		font-style: italic;
		line-height: 1.5;
		color: color-mix(in srgb, var(--se-vellum) 74%, transparent);
		max-width: 34rem;
	}
	cite {
		font-style: normal;
	}

	/* Saint Elmo's fire: a blue corona at the tip of the crozier, kindled once on load. */
	.corona {
		position: absolute;
		left: calc(10px + (100% - 20px) * 0.429);
		top: calc(10px + (100% - 20px) * 0.094);
		width: 18%;
		aspect-ratio: 1;
		translate: -50% -50%;
		border-radius: 50%;
		background: radial-gradient(
			circle,
			rgb(205 218 255 / 0.85) 0%,
			color-mix(in srgb, var(--se-corona) 70%, transparent) 22%,
			color-mix(in srgb, var(--se-corona) 22%, transparent) 48%,
			transparent 70%
		);
		mix-blend-mode: screen;
		pointer-events: none;
		opacity: 0.4;
		animation: kindle 3.2s ease-out 0.6s both;
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
			opacity: 0.4;
			scale: 1;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.corona {
			animation: none;
			opacity: 0.4;
		}
	}

	/* The leaf: one vellum page laid on the lapis, written in ink with red rubrics */
	.leaf {
		position: relative;
		padding: 3rem 1.5rem;
		background: var(--se-vellum);
		color: var(--ink);
		border: 1px solid #b89a52;
		box-shadow:
			inset 0 0 0 6px var(--se-vellum),
			inset 0 0 0 7px color-mix(in srgb, var(--se-gold) 70%, transparent),
			0 40px 80px -40px rgb(0 0 0 / 0.6);
		scroll-margin-top: 2rem;
	}
	@media (min-width: 768px) {
		.leaf {
			padding: 4.5rem 4.5rem 4rem;
		}
	}
	.leaf h2,
	.mandate h2 {
		font-family: var(--font-smallcaps);
		font-weight: 500;
		font-size: clamp(1.75rem, 3vw, 2.375rem);
		line-height: 1.15;
		letter-spacing: 0.01em;
	}
	.leaf-intro {
		margin-top: 1.25rem;
		max-width: 40rem;
		font-size: 1.1875rem;
		color: var(--ink);
	}
	.initial {
		float: left;
		margin: 0.35rem 0.6rem 0 0;
		font-family: var(--font-blackletter);
		font-size: 4.4rem;
		line-height: 0.75;
		color: var(--se-vermilion);
	}
	.folios {
		display: grid;
		gap: 2.5rem 3.5rem;
		margin-top: 3rem;
		padding: 0;
		list-style: none;
	}
	@media (min-width: 720px) {
		.folios {
			grid-template-columns: repeat(2, 1fr);
		}
	}
	@media (min-width: 1100px) {
		.folios {
			grid-template-columns: repeat(3, 1fr);
		}
	}
	.folios li {
		border-top: 1px solid color-mix(in srgb, var(--ink) 22%, transparent);
		padding-top: 1rem;
	}
	.numeral {
		display: block;
		font-family: var(--font-smallcaps);
		font-size: 1.75rem;
		letter-spacing: 0.04em;
		line-height: 1;
		color: var(--se-vermilion);
	}
	.folios h3 {
		margin-top: 0.5rem;
		font-size: 1.3125rem;
		font-weight: 700;
	}
	.folios p {
		margin-top: 0.4rem;
		font-size: 1.0625rem;
		line-height: 1.58;
		color: var(--ink-soft);
	}
	.folios .artefact {
		margin-top: 0.9rem;
		font-family: var(--font-mono);
		font-size: 0.8125rem;
		color: var(--ink);
		padding-left: 0.75rem;
		border-left: 2px solid var(--se-vermilion);
	}

	/* Mandate */
	.mandate {
		display: grid;
		gap: 3rem;
		padding-block: 6rem;
	}
	@media (min-width: 1024px) {
		.mandate {
			grid-template-columns: 22rem 1fr;
			gap: 5rem;
			align-items: start;
		}
	}
	.side-plate {
		max-width: 22rem;
	}
	.mandate-text {
		max-width: 40rem;
	}
	.mandate h2 {
		color: var(--se-vellum);
		text-wrap: balance;
	}
	.mandate-text > p {
		margin-top: 1.25rem;
		color: color-mix(in srgb, var(--se-vellum) 86%, transparent);
	}
	.tiers {
		margin-top: 2rem;
		border-top: 1px solid color-mix(in srgb, var(--se-gold) 60%, transparent);
	}
	.tiers div {
		display: grid;
		gap: 0.25rem 2rem;
		padding-block: 1.1rem;
		border-bottom: 1px solid color-mix(in srgb, var(--se-gold) 35%, transparent);
	}
	@media (min-width: 640px) {
		.tiers div {
			grid-template-columns: 12rem 1fr;
		}
	}
	.tiers dt {
		font-weight: 700;
		color: var(--se-vellum);
	}
	.tiers dd {
		color: color-mix(in srgb, var(--se-vellum) 80%, transparent);
	}

	/* Colophon */
	.colophon {
		padding-block: 3rem 4.5rem;
		border-top: 1px solid color-mix(in srgb, var(--se-gold) 55%, transparent);
	}
	.colophon h2 {
		font-family: var(--font-smallcaps);
		font-weight: 500;
		font-size: 1.25rem;
		color: var(--se-gold);
	}
	.colophon-grid {
		display: grid;
		gap: 1rem 3rem;
		margin-top: 1rem;
		font-size: 0.9375rem;
		line-height: 1.6;
		color: color-mix(in srgb, var(--se-vellum) 72%, transparent);
	}
	@media (min-width: 768px) {
		.colophon-grid {
			grid-template-columns: repeat(3, 1fr);
		}
	}
	.colophon-mark {
		margin-top: 2rem;
		height: 2.75rem;
		width: auto;
		border-radius: 3px;
	}
</style>
