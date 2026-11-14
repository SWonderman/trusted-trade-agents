<script lang="ts">
	import './layout.css';
	import { ModeWatcher } from 'mode-watcher';
	import { Toaster } from '#lib/components/ui/sonner/index.js';
	import * as Tooltip from '#lib/components/ui/tooltip/index.js';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<ModeWatcher defaultMode="system" />
<Toaster position="bottom-right" richColors />
<Tooltip.Provider delayDuration={300}>
	{@render children()}
</Tooltip.Provider>
