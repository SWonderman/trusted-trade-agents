<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import Drawer from '#lib/components/ui/Drawer.svelte';
	import type { PageProps } from './$types';

	let { form }: PageProps = $props();

	let saving = $state(false);
	let errors = $derived<Record<string, string>>(
		form && 'errors' in form ? (form.errors ?? {}) : {}
	);
	let v = $derived<Record<string, string>>(form && 'values' in form ? (form.values ?? {}) : {});

	const claims = [
		['FREE_FROM:LACTOSE', 'Lactose-free'],
		['FREE_FROM:GLUTEN', 'Gluten-free'],
		['FREE_FROM:MILK', 'Milk-free']
	] as const;
	const diets = [
		['VEGAN', 'Vegan'],
		['VEGETARIAN', 'Vegetarian']
	] as const;
	const allergens = [
		['AM', 'Milk'],
		['AW', 'Gluten cereals'],
		['AE', 'Egg'],
		['AN', 'Tree nuts'],
		['AP', 'Peanuts'],
		['AY', 'Soy'],
		['AF', 'Fish']
	] as const;
</script>

<svelte:head><title>New agent · Saint Elmo</title></svelte:head>

{#snippet error(key: string)}
	{#if errors[key]}<p class="mt-1.5 text-sm text-stop" id="{key}-error">{errors[key]}</p>{/if}
{/snippet}

<Drawer
	title="New agent"
	description="Name the task it does and set its mandate. You can issue its key next."
	width="40rem"
	onclose={() => goto(resolve('agents'), { reset: false })}
>
	<form
		id="new-agent"
		method="POST"
		class="space-y-8"
		use:enhance={() => {
			saving = true;
			return async ({ update }) => {
				await update({ reset: false });
				saving = false;
			};
		}}
	>
		<fieldset class="space-y-4">
			<legend class="mb-3 text-base font-semibold text-ink">The agent</legend>
			<div>
				<label for="name" class="field-label">Name</label>
				<input
					id="name"
					name="name"
					class="input code"
					placeholder="weekend-brunch"
					value={v.name ?? ''}
					required
					aria-invalid={errors.name ? 'true' : undefined}
					aria-describedby="name-hint {errors.name ? 'name-error' : ''}"
				/>
				<p id="name-hint" class="field-hint">Shown in the audit trail and approval inbox.</p>
				{@render error('name')}
			</div>
			<div>
				<label for="purpose" class="field-label">What it’s for</label>
				<input
					id="purpose"
					name="purpose"
					class="input"
					placeholder="Orders brunch supplies for the weekend buffet."
					value={v.purpose ?? ''}
				/>
			</div>
		</fieldset>

		<fieldset class="space-y-4 border-t border-line pt-6">
			<legend class="mb-3 text-base font-semibold text-ink">Spend</legend>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="autoApproveUpTo" class="field-label">Decides alone up to (€)</label>
					<input
						id="autoApproveUpTo"
						name="autoApproveUpTo"
						type="number"
						min="0"
						step="50"
						class="input tabular"
						value={v.autoApproveUpTo ?? '500'}
					/>
					<p class="field-hint">Above this, orders wait for a person.</p>
					{@render error('autoApproveUpTo')}
				</div>
				<div>
					<label for="maxOrderTotal" class="field-label">Order limit (€)</label>
					<input
						id="maxOrderTotal"
						name="maxOrderTotal"
						type="number"
						min="1"
						step="50"
						class="input tabular"
						value={v.maxOrderTotal ?? '1500'}
					/>
					<p class="field-hint">Above this, orders are rejected.</p>
					{@render error('maxOrderTotal')}
				</div>
				<div>
					<label for="periodSpendCap" class="field-label">Spend cap (€)</label>
					<input
						id="periodSpendCap"
						name="periodSpendCap"
						type="number"
						min="1"
						step="100"
						class="input tabular"
						value={v.periodSpendCap ?? '4000'}
					/>
					{@render error('periodSpendCap')}
				</div>
				<div>
					<label for="spendPeriod" class="field-label">Per</label>
					<select id="spendPeriod" name="spendPeriod" class="input">
						<option value="WEEK" selected={v.spendPeriod !== 'MONTH'}>Week</option>
						<option value="MONTH" selected={v.spendPeriod === 'MONTH'}>Month</option>
					</select>
				</div>
			</div>
		</fieldset>

		<fieldset class="space-y-4 border-t border-line pt-6">
			<legend class="mb-3 text-base font-semibold text-ink">Assortment</legend>
			<div>
				<label for="allowedCategoryCodes" class="field-label">Only these category codes</label>
				<input
					id="allowedCategoryCodes"
					name="allowedCategoryCodes"
					class="input code"
					placeholder="1101, 1102"
					value={v.allowedCategoryCodes ?? ''}
				/>
				<p class="field-hint">
					Leave empty to allow every category. Unknown codes are rejected when saved.
				</p>
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="allowedVendors" class="field-label">Only these vendors</label>
					<input
						id="allowedVendors"
						name="allowedVendors"
						class="input"
						placeholder="Any vendor"
						value={v.allowedVendors ?? ''}
					/>
				</div>
				<div>
					<label for="allowedCountriesOfOrigin" class="field-label">Only these origins</label>
					<input
						id="allowedCountriesOfOrigin"
						name="allowedCountriesOfOrigin"
						class="input code"
						placeholder="fi, se"
						value={v.allowedCountriesOfOrigin ?? ''}
					/>
				</div>
			</div>
		</fieldset>

		<fieldset class="border-t border-line pt-6">
			<legend class="mb-1 text-base font-semibold text-ink">Requirements</legend>
			<p class="mb-4 text-sm text-muted">
				Products must declare these. Missing manufacturer data counts as not declared.
			</p>
			<div class="grid gap-6 sm:grid-cols-2">
				<fieldset>
					<legend class="field-label">Required claims and diets</legend>
					<div class="space-y-2">
						{#each claims as [code, label] (code)}
							<label class="flex items-center gap-2 text-sm text-ink">
								<input type="checkbox" name="requiredClaims" value={code} class="rounded-sm" />
								{label} <span class="code text-faint">{code.replace(':', '_')}</span>
							</label>
						{/each}
						{#each diets as [code, label] (code)}
							<label class="flex items-center gap-2 text-sm text-ink">
								<input type="checkbox" name="requiredDiets" value={code} class="rounded-sm" />
								{label}
							</label>
						{/each}
					</div>
				</fieldset>
				<fieldset>
					<legend class="field-label">Excluded allergens</legend>
					<div class="grid grid-cols-2 gap-2">
						{#each allergens as [code, label] (code)}
							<label class="flex items-center gap-2 text-sm text-ink">
								<input type="checkbox" name="excludedAllergens" value={code} class="rounded-sm" />
								{label}
							</label>
						{/each}
					</div>
					<label for="allergenStrictness" class="field-label mt-4">How strict</label>
					<select id="allergenStrictness" name="allergenStrictness" class="input">
						<option value="contains">Block products that contain them</option>
						<option value="may_contain">Also block “may contain”</option>
						<option value="declared_free">Only products declared free from them</option>
					</select>
				</fieldset>
			</div>
		</fieldset>

		<fieldset class="space-y-4 border-t border-line pt-6">
			<legend class="mb-3 text-base font-semibold text-ink">Substitutes and delivery</legend>
			<div class="space-y-2">
				{#each [['IF_REQUIREMENTS_HOLD', 'Allowed when every requirement still holds'], ['ALWAYS_NEEDS_APPROVAL', 'Every substitute goes to a person'], ['NEVER', 'Never substitute']] as [value, label] (value)}
					<label class="flex items-center gap-2 text-sm text-ink">
						<input
							type="radio"
							name="substitutionPolicy"
							{value}
							checked={value === 'IF_REQUIREMENTS_HOLD'}
						/>
						{label}
					</label>
				{/each}
			</div>
			<div class="grid gap-4 sm:grid-cols-2">
				<div>
					<label for="maxSubstitutePriceIncreasePct" class="field-label"
						>Substitute may cost at most (% more)</label
					>
					<input
						id="maxSubstitutePriceIncreasePct"
						name="maxSubstitutePriceIncreasePct"
						type="number"
						min="0"
						max="100"
						class="input tabular"
						value={v.maxSubstitutePriceIncreasePct ?? '10'}
					/>
					<p class="field-hint">Compared per litre or kg.</p>
				</div>
				<div>
					<label for="minDeliveryReliability" class="field-label"
						>Minimum delivery reliability (%)</label
					>
					<input
						id="minDeliveryReliability"
						name="minDeliveryReliability"
						type="number"
						min="0"
						max="100"
						class="input tabular"
						placeholder="No minimum"
						value={v.minDeliveryReliability ?? ''}
					/>
				</div>
			</div>
			<label class="flex items-center gap-2 text-sm text-ink">
				<input type="checkbox" name="laterDeliveryNeedsApproval" checked class="rounded-sm" />
				A later delivery date than asked for needs a person
			</label>
		</fieldset>

		{#if form && 'error' in form && form.error}
			<p role="alert" class="rounded-sm bg-stop-wash px-3 py-2 text-sm text-stop">{form.error}</p>
		{/if}
	</form>

	{#snippet footer()}
		<a href={resolve('agents')} class="btn btn-quiet">Cancel</a>
		<button form="new-agent" class="btn btn-primary" disabled={saving}>
			{saving ? 'Creating…' : 'Create agent'}
		</button>
	{/snippet}
</Drawer>
