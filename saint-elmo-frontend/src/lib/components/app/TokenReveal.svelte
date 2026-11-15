<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import CopyIcon from '@lucide/svelte/icons/copy';
	import KeyRoundIcon from '@lucide/svelte/icons/key-round';
	import * as InputGroup from '#lib/components/ui/input-group/index.js';

	let { secret, label, mcpUrl }: { secret: string; label: string; mcpUrl: string } = $props();
	// Which copy button was used last ('token' or a snippet's title), so only it says so.
	let copied = $state<string | null>(null);
	// The repo's buyer-agent demo folder: its .mcp.json reads SAINT_ELMO_AGENT_KEY. Keep in step
	// with demo/buyer-agent/ if it moves.
	const DEMO_FOLDER = 'demo/buyer-agent';

	// The token is already on screen in plain text, once, so the snippets carry it too.
	let snippets = $derived([
		{
			title: 'Claude Code, from any folder',
			text: `claude mcp add --transport http saint-elmo ${mcpUrl} --header "X-Agent-Key: ${secret}"`
		},
		{
			title: 'In this repo',
			text: `export SAINT_ELMO_AGENT_KEY=${secret}\ncd ${DEMO_FOLDER} && claude`
		}
	]);

	async function copy(id: string, text: string) {
		try {
			await navigator.clipboard.writeText(text);
			copied = id;
			setTimeout(() => {
				if (copied === id) copied = null;
			}, 2000);
		} catch {
			// Clipboard blocked: the text is selectable, so it can still be copied by hand.
		}
	}
</script>

{#snippet copyButton(id: string, text: string)}
	<InputGroup.Button onclick={() => copy(id, text)} size="xs">
		{#if copied === id}<CheckIcon />Copied{:else}<CopyIcon />Copy{/if}
	</InputGroup.Button>
{/snippet}

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
					{@render copyButton('token', secret)}
				</InputGroup.Addon>
			</InputGroup.Root>
			<p class="mt-2 text-xs text-muted-foreground">
				Give it to the MCP client as the <span class="code">X-Agent-Key</span> header, or as
				<span class="code">Authorization: Bearer</span>. To connect Claude Code:
			</p>
			{#each snippets as snippet (snippet.title)}
				<div class="mt-3 rounded-md border bg-card">
					<div class="flex items-center justify-between gap-2 border-b py-1 pr-1 pl-3">
						<span class="text-xs font-medium text-muted-foreground">{snippet.title}</span>
						{@render copyButton(snippet.title, snippet.text)}
					</div>
					<pre
						class="overflow-x-auto p-3 code whitespace-pre text-foreground/80">{snippet.text}</pre>
				</div>
			{/each}
		</div>
	</div>
</div>
