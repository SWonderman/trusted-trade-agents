<script lang="ts">
	import Icon from './Icon.svelte';

	let { secret, label }: { secret: string; label: string } = $props();
	let copied = $state(false);

	async function copy() {
		try {
			await navigator.clipboard.writeText(secret);
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			// Clipboard blocked: the field is selectable, so the key can still be copied by hand.
		}
	}
</script>

<div class="rounded-md border border-ok/40 bg-ok-wash p-4" role="status">
	<p class="font-semibold text-ink">Copy the key for “{label}” now</p>
	<p class="mt-0.5 text-sm text-muted">
		This is the only time it’s shown. Saint Elmo keeps no copy, so a lost key has to be revoked and
		replaced.
	</p>
	<div class="mt-3 flex gap-2">
		<input
			readonly
			value={secret}
			aria-label="New agent key"
			class="input code flex-1 bg-panel"
			onfocus={(e) => e.currentTarget.select()}
		/>
		<button type="button" class="btn" onclick={copy}>
			<Icon name={copied ? 'check' : 'copy'} />
			{copied ? 'Copied' : 'Copy'}
		</button>
	</div>
	<p class="mt-2 text-xs text-muted">
		Give it to the MCP client as the <span class="code">X-Agent-Key</span> header, or as
		<span class="code">Authorization: Bearer</span>.
	</p>
</div>
