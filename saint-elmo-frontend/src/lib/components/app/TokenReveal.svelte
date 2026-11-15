<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import * as InputGroup from '#lib/components/ui/input-group/index.js';

	let { secret, label }: { secret: string; label: string } = $props();
	let copied = $state(false);

	async function copy() {
		try {
			await navigator.clipboard.writeText(secret);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			// Clipboard blocked: the field is selectable, so the token can still be copied by hand.
		}
	}
</script>

<div class="rounded-xl border border-ok/30 bg-ok/6 p-4" role="status">
	<div class="flex gap-3">
		<span class="grid size-8 shrink-0 place-items-center rounded-lg bg-ok/12 text-ok">
			<KeyRoundIcon class="size-4" aria-hidden="true" />
		</span>
		<div class="min-w-0 flex-1">
			<p class="text-sm font-semibold">Copy the token for “{label}” now</p>
			<p class="mt-0.5 text-sm text-muted-foreground">
				This is the only time it’s shown. Saint Elmo keeps no copy, so a lost token has to be
				revoked and replaced.
			</p>
			<InputGroup.Root class="mt-3 bg-card">
				<InputGroup.Input
					readonly
					value={secret}
					aria-label="New Agent token"
					class="code"
					onfocus={(e) => e.currentTarget.select()}
				/>
				<InputGroup.Addon align="inline-end">
					<InputGroup.Button onclick={copy} size="xs">
						{#if copied}<CheckIcon />Copied{:else}<CopyIcon />Copy{/if}
					</InputGroup.Button>
				</InputGroup.Addon>
			</InputGroup.Root>
			<p class="mt-2 text-xs text-muted-foreground">
				Give it to the MCP client as the <span class="code">X-Agent-Key</span> header, or as
				<span class="code">Authorization: Bearer</span>.
			</p>
		</div>
	</div>
</div>
