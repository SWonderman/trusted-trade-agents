<script lang="ts" module>
	/** Hand-drawn 24px stroke icons; only the ones the app uses. */
	const paths = {
		check: 'M5 12.5l4.5 4.5L19 7.5',
		hand: 'M8 13V5.5a1.5 1.5 0 013 0V11m0-6.5a1.5 1.5 0 013 0V11m0-5a1.5 1.5 0 013 0v7.5c0 4-2.5 6.5-6 6.5-2.6 0-4.2-1.3-5.6-3.4L4.2 13.3a1.4 1.4 0 012.2-1.7L8 13',
		x: 'M6 6l12 12M18 6L6 18',
		info: 'M12 8h.01M11 12h1v5h1M12 21a9 9 0 100-18 9 9 0 000 18z',
		inbox:
			'M3 13l2.5-7.5A2 2 0 017.4 4h9.2a2 2 0 011.9 1.5L21 13M3 13v5a2 2 0 002 2h14a2 2 0 002-2v-5M3 13h5l1.5 2.5h5L16 13h5',
		agents:
			'M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2.5 20a6.5 6.5 0 0113 0M16 4.3a3.5 3.5 0 010 6.4M18.5 20a6.5 6.5 0 00-3-5.5',
		scroll:
			'M7 4h11a2 2 0 012 2v1h-4M7 4a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7M7 4a2 2 0 012 2v0M9 10h6M9 14h6',
		eye: 'M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12zM12 15a3 3 0 100-6 3 3 0 000 6z',
		key: 'M14.5 9.5a4 4 0 11-1.2-2.9L21 14v3h-3v-2h-2v-2h-2.2M8.5 10.5h.01',
		copy: 'M9 9h10a1 1 0 011 1v10a1 1 0 01-1 1H9a1 1 0 01-1-1V10a1 1 0 011-1zM5 15H4a1 1 0 01-1-1V4a1 1 0 011-1h10a1 1 0 011 1v1',
		chevronRight: 'M9 6l6 6-6 6',
		chevronDown: 'M6 9l6 6 6-6',
		sun: 'M12 16a4 4 0 100-8 4 4 0 000 8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
		moon: 'M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z',
		logout: 'M15 4h3a2 2 0 012 2v12a2 2 0 01-2 2h-3M10 17l5-5-5-5M15 12H4',
		plus: 'M12 5v14M5 12h14',
		flask: 'M9 3h6M10 3v6.5L4.5 18a2 2 0 001.7 3h11.6a2 2 0 001.7-3L14 9.5V3M7 15h10',
		shield: 'M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6l8-3zM9 12l2 2 4-4',
		lock: 'M6 11h12v9H6zM8.5 11V8a3.5 3.5 0 017 0v3',
		arrowRight: 'M5 12h14M13 6l6 6-6 6',
		clock: 'M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5l3 2',
		truck:
			'M3 6h11v10H3zM14 9h4l3 3v4h-7M7.5 19a1.5 1.5 0 100-3 1.5 1.5 0 000 3zM17.5 19a1.5 1.5 0 100-3 1.5 1.5 0 000 3z',
		leaf: 'M5 19c0-8 5-13 15-14-1 10-6 15-14 15M5 19l7-7',
		swap: 'M7 4L3 8l4 4M3 8h14M17 20l4-4-4-4M21 16H7',
		menu: 'M4 7h16M4 12h16M4 17h16',
		ban: 'M12 21a9 9 0 100-18 9 9 0 000 18zM5.7 5.7l12.6 12.6'
	} as const;
	export type IconName = keyof typeof paths;
</script>

<script lang="ts">
	let { name, size = 16, label }: { name: IconName; size?: number; label?: string } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.75"
	stroke-linecap="round"
	stroke-linejoin="round"
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
	class="shrink-0"
>
	<path d={paths[name]} />
</svg>
