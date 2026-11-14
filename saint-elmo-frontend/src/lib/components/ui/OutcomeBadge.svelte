<script lang="ts">
	import type { ReasonSeverity } from '#lib/api/types.js';
	import { outcomeLabel } from '#lib/format.js';
	import Icon, { type IconName } from './Icon.svelte';

	let {
		outcome,
		label,
		size = 'md'
	}: { outcome: ReasonSeverity | 'neutral'; label?: string; size?: 'sm' | 'md' } = $props();

	const icons: Record<ReasonSeverity | 'neutral', IconName> = {
		AUTO_APPROVE: 'check',
		NEEDS_HUMAN: 'hand',
		REJECT: 'ban',
		INFO: 'info',
		neutral: 'info'
	};

	let text = $derived(label ?? (outcome === 'neutral' ? '' : outcomeLabel[outcome]));
</script>

<span
	class={[
		'inline-flex items-center gap-1.5 rounded-sm font-semibold whitespace-nowrap',
		size === 'sm' ? 'px-1.5 py-0.5 text-xs' : 'px-2 py-1 text-[0.8125rem]',
		{
			'bg-ok-wash text-ok': outcome === 'AUTO_APPROVE',
			'bg-hold-wash text-hold': outcome === 'NEEDS_HUMAN',
			'bg-stop-wash text-stop': outcome === 'REJECT',
			'bg-sunken text-muted': outcome === 'INFO' || outcome === 'neutral'
		}
	]}
>
	<Icon name={icons[outcome]} size={size === 'sm' ? 12 : 14} />
	{text}
</span>
