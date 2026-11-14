<script lang="ts">
	import { resolve } from '$app/paths';
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { Button } from '#lib/components/ui/button/index.js';
	import { Checkbox } from '#lib/components/ui/checkbox/index.js';
	import * as Field from '#lib/components/ui/field/index.js';
	import { Input } from '#lib/components/ui/input/index.js';
	import * as InputGroup from '#lib/components/ui/input-group/index.js';
	import * as RadioGroup from '#lib/components/ui/radio-group/index.js';
	import * as Select from '#lib/components/ui/select/index.js';
	import * as Sheet from '#lib/components/ui/sheet/index.js';
	import { Spinner } from '#lib/components/ui/spinner/index.js';
	import type { PageProps } from './$types';

	let { form }: PageProps = $props();

	let saving = $state(false);
	let errors = $derived<Record<string, string>>(
		form && 'errors' in form ? (form.errors ?? {}) : {}
	);
	let v = $derived<Record<string, string>>(form && 'values' in form ? (form.values ?? {}) : {});

	let spendPeriod = $state('WEEK');
	let strictness = $state('contains');
	let substitution = $state('IF_REQUIREMENTS_HOLD');

	const periods: Record<string, string> = { WEEK: 'Week', MONTH: 'Month' };
	const strictnessLabel: Record<string, string> = {
		contains: 'Block products that contain them',
		may_contain: 'Also block “may contain”',
		declared_free: 'Only products declared free from them'
	};
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
	const substitutions = [
		['IF_REQUIREMENTS_HOLD', 'Allowed when every requirement still holds'],
		['ALWAYS_NEEDS_APPROVAL', 'Every substitute goes to a person'],
		['NEVER', 'Never substitute']
	] as const;
</script>

<svelte:head><title>New agent · Saint Elmo</title></svelte:head>

{#snippet money(id: string, label: string, value: string, step: number, hint?: string)}
	<Field.Field data-invalid={errors[id] ? true : undefined}>
		<Field.Label for={id}>{label}</Field.Label>
		<InputGroup.Root>
			<InputGroup.Addon><InputGroup.Text>€</InputGroup.Text></InputGroup.Addon>
			<InputGroup.Input
				{id}
				name={id}
				type="number"
				min="0"
				{step}
				class="tabular"
				value={v[id] ?? value}
				aria-invalid={errors[id] ? 'true' : undefined}
			/>
		</InputGroup.Root>
		{#if errors[id]}<Field.Error>{errors[id]}</Field.Error>
		{:else if hint}<Field.Description>{hint}</Field.Description>{/if}
	</Field.Field>
{/snippet}

<Sheet.Root
	open
	onOpenChange={(open) => {
		if (!open) goto(resolve('agents'), { reset: false });
	}}
>
	<Sheet.Content side="right" class="gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-2xl">
		<Sheet.Header class="border-b px-6 pt-6 pb-5">
			<Sheet.Title class="font-display-tight text-2xl">New agent</Sheet.Title>
			<Sheet.Description>
				Name the task it does and set its mandate. You can issue its Agent token next.
			</Sheet.Description>
		</Sheet.Header>

		<form
			id="new-agent"
			method="POST"
			class="flex-1 overflow-y-auto px-6 py-6"
			use:enhance={() => {
				saving = true;
				return async ({ update }) => {
					await update({ reset: false });
					saving = false;
				};
			}}
		>
			<Field.Group>
				<Field.Set>
					<Field.Legend>The agent</Field.Legend>
					<Field.Group>
						<Field.Field data-invalid={errors.name ? true : undefined}>
							<Field.Label for="name">Name</Field.Label>
							<Input
								id="name"
								name="name"
								class="code"
								placeholder="weekend-brunch"
								value={v.name ?? ''}
								required
								aria-invalid={errors.name ? 'true' : undefined}
							/>
							{#if errors.name}<Field.Error>{errors.name}</Field.Error>
							{:else}<Field.Description
									>Shown in the audit trail and on approvals. Lowercase, digits and hyphens.</Field.Description
								>{/if}
						</Field.Field>
						<Field.Field>
							<Field.Label for="purpose">What it’s for</Field.Label>
							<Input
								id="purpose"
								name="purpose"
								placeholder="Orders brunch supplies for the weekend buffet."
								value={v.purpose ?? ''}
							/>
						</Field.Field>
					</Field.Group>
				</Field.Set>

				<Field.Separator />

				<Field.Set>
					<Field.Legend>Spend</Field.Legend>
					<Field.Group class="grid gap-4 sm:grid-cols-2">
						{@render money(
							'autoApproveUpTo',
							'Decides alone up to',
							'500',
							50,
							'Above this, orders wait for a person.'
						)}
						{@render money(
							'maxOrderTotal',
							'Order limit',
							'1500',
							50,
							'Above this, orders are rejected.'
						)}
						{@render money('periodSpendCap', 'Spend cap', '4000', 100)}
						<Field.Field>
							<Field.Label for="spendPeriod">Per</Field.Label>
							<Select.Root type="single" name="spendPeriod" bind:value={spendPeriod}>
								<Select.Trigger id="spendPeriod" class="w-full"
									>{periods[spendPeriod]}</Select.Trigger
								>
								<Select.Content>
									<Select.Item value="WEEK" label="Week" />
									<Select.Item value="MONTH" label="Month" />
								</Select.Content>
							</Select.Root>
						</Field.Field>
					</Field.Group>
				</Field.Set>

				<Field.Separator />

				<Field.Set>
					<Field.Legend>Assortment</Field.Legend>
					<Field.Group>
						<Field.Field>
							<Field.Label for="allowedCategoryCodes">Only these category codes</Field.Label>
							<Input
								id="allowedCategoryCodes"
								name="allowedCategoryCodes"
								class="code"
								placeholder="10400, 10401"
								value={v.allowedCategoryCodes ?? ''}
							/>
							<Field.Description>
								Leave empty to allow every category. The Catalog page lists the codes.
							</Field.Description>
						</Field.Field>
						<div class="grid gap-4 sm:grid-cols-2">
							<Field.Field>
								<Field.Label for="allowedVendors">Only these vendors</Field.Label>
								<Input
									id="allowedVendors"
									name="allowedVendors"
									placeholder="Any vendor"
									value={v.allowedVendors ?? ''}
								/>
							</Field.Field>
							<Field.Field>
								<Field.Label for="allowedCountriesOfOrigin">Only these origins</Field.Label>
								<Input
									id="allowedCountriesOfOrigin"
									name="allowedCountriesOfOrigin"
									class="code"
									placeholder="fi, se"
									value={v.allowedCountriesOfOrigin ?? ''}
								/>
							</Field.Field>
						</div>
					</Field.Group>
				</Field.Set>

				<Field.Separator />

				<Field.Set>
					<Field.Legend>Requirements</Field.Legend>
					<Field.Description>
						Products must declare these. Missing manufacturer data counts as not declared.
					</Field.Description>
					<div class="grid gap-6 sm:grid-cols-2">
						<Field.Set>
							<Field.Label>Required claims and diets</Field.Label>
							<Field.Group class="gap-2.5">
								{#each [...claims, ...diets] as [code, label] (code)}
									<Field.Field orientation="horizontal">
										<Checkbox
											id="req-{code}"
											name={code.includes(':') ? 'requiredClaims' : 'requiredDiets'}
											value={code}
										/>
										<Field.Label for="req-{code}" class="font-normal">
											{label}
											{#if code.includes(':')}<span class="code text-muted-foreground"
													>{code.replace(':', '_')}</span
												>{/if}
										</Field.Label>
									</Field.Field>
								{/each}
							</Field.Group>
						</Field.Set>
						<Field.Set>
							<Field.Label>Excluded allergens</Field.Label>
							<Field.Group class="grid grid-cols-2 gap-2.5">
								{#each allergens as [code, label] (code)}
									<Field.Field orientation="horizontal">
										<Checkbox id="allergen-{code}" name="excludedAllergens" value={code} />
										<Field.Label for="allergen-{code}" class="font-normal">{label}</Field.Label>
									</Field.Field>
								{/each}
							</Field.Group>
							<Field.Field class="mt-2">
								<Field.Label for="allergenStrictness">How strict</Field.Label>
								<Select.Root type="single" name="allergenStrictness" bind:value={strictness}>
									<Select.Trigger id="allergenStrictness" class="w-full"
										>{strictnessLabel[strictness]}</Select.Trigger
									>
									<Select.Content>
										{#each Object.entries(strictnessLabel) as [value, label] (value)}
											<Select.Item {value} {label} />
										{/each}
									</Select.Content>
								</Select.Root>
							</Field.Field>
						</Field.Set>
					</div>
				</Field.Set>

				<Field.Separator />

				<Field.Set>
					<Field.Legend>Substitutes and delivery</Field.Legend>
					<RadioGroup.Root name="substitutionPolicy" bind:value={substitution} class="gap-2.5">
						{#each substitutions as [value, label] (value)}
							<Field.Field orientation="horizontal">
								<RadioGroup.Item {value} id="sub-{value}" />
								<Field.Label for="sub-{value}" class="font-normal">{label}</Field.Label>
							</Field.Field>
						{/each}
					</RadioGroup.Root>
					<div class="grid gap-4 sm:grid-cols-2">
						<Field.Field>
							<Field.Label for="maxSubstitutePriceIncreasePct"
								>Substitute may cost at most</Field.Label
							>
							<InputGroup.Root>
								<InputGroup.Input
									id="maxSubstitutePriceIncreasePct"
									name="maxSubstitutePriceIncreasePct"
									type="number"
									min="0"
									max="100"
									class="tabular"
									value={v.maxSubstitutePriceIncreasePct ?? '10'}
								/>
								<InputGroup.Addon align="inline-end"
									><InputGroup.Text>% more</InputGroup.Text></InputGroup.Addon
								>
							</InputGroup.Root>
							<Field.Description>Compared per litre or kg.</Field.Description>
						</Field.Field>
						<Field.Field>
							<Field.Label for="minDeliveryReliability">Minimum delivery reliability</Field.Label>
							<InputGroup.Root>
								<InputGroup.Input
									id="minDeliveryReliability"
									name="minDeliveryReliability"
									type="number"
									min="0"
									max="100"
									class="tabular"
									placeholder="No minimum"
									value={v.minDeliveryReliability ?? ''}
								/>
								<InputGroup.Addon align="inline-end"
									><InputGroup.Text>%</InputGroup.Text></InputGroup.Addon
								>
							</InputGroup.Root>
						</Field.Field>
					</div>
					<Field.Field orientation="horizontal">
						<Checkbox id="laterDelivery" name="laterDeliveryNeedsApproval" checked />
						<Field.Label for="laterDelivery" class="font-normal">
							A later delivery date than asked for needs a person
						</Field.Label>
					</Field.Field>
				</Field.Set>

				{#if form && 'error' in form && form.error}
					<p role="alert" class="rounded-lg bg-stop/8 px-3 py-2 text-sm text-stop">{form.error}</p>
				{/if}
			</Field.Group>
		</form>

		<Sheet.Footer class="flex-row justify-end border-t px-6 py-4">
			<Button href={resolve('agents')} variant="ghost">Cancel</Button>
			<Button type="submit" form="new-agent" disabled={saving}>
				{#if saving}<Spinner />Creating…{:else}Create agent{/if}
			</Button>
		</Sheet.Footer>
	</Sheet.Content>
</Sheet.Root>
