<script lang="ts">
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import CircleAlertIcon from '@lucide/svelte/icons/circle-alert';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import InfoIcon from '@lucide/svelte/icons/info';
	import CircleIcon from '@lucide/svelte/icons/circle';
	import type { ReasonSeverity } from '#lib/api/types.js';
	import { outcomeLabel } from '#lib/format.js';
	import { cn } from '#lib/utils.js';

	type Tone = ReasonSeverity | 'neutral';

	let {
		outcome,
		label,
		class: className
	}: { outcome: Tone; label?: string; class?: string } = $props();

	const tones = {
		AUTO_APPROVE: { icon: CircleCheckIcon, cls: 'bg-ok/10 text-ok ring-ok/20' },
		NEEDS_HUMAN: { icon: CircleAlertIcon, cls: 'bg-hold/12 text-hold ring-hold/25' },
		REJECT: { icon: CircleXIcon, cls: 'bg-stop/10 text-stop ring-stop/20' },
		INFO: { icon: InfoIcon, cls: 'bg-muted text-muted-foreground ring-border' },
		neutral: { icon: CircleIcon, cls: 'bg-muted text-muted-foreground ring-border' }
	} as const;

	let tone = $derived(tones[outcome]);
	let text = $derived(label ?? (outcome === 'neutral' ? '' : outcomeLabel[outcome]));
</script>

<!-- Icon shape carries the outcome too, so it never depends on colour alone. -->
<span
	class={cn(
		'inline-flex h-5.5 shrink-0 items-center gap-1 rounded-full px-2 text-xs font-medium whitespace-nowrap ring-1 ring-inset',
		tone.cls,
		className
	)}
>
	<tone.icon class="size-3.5" aria-hidden="true" />
	{text}
</span>
