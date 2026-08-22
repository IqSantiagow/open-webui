<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import type { KanbanCard, KanbanColumn } from '$lib/apis/kanban';
	import NativeSelect from '$lib/components/common/NativeSelect.svelte';
	import Tags from '$lib/components/common/Tags.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let card: KanbanCard;
	export let columns: KanbanColumn[] = [];

	export let onUpdate: (fields: Record<string, any>) => void = () => {};
	export let onMove: (columnId: string) => void = () => {};

	const fieldClassName =
		'w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-xs text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500';

	const priorityOptions = [
		{ value: '', label: $i18n.t('None') },
		{ value: 'low', label: $i18n.t('Low') },
		{ value: 'medium', label: $i18n.t('Medium') },
		{ value: 'high', label: $i18n.t('High') }
	];

	$: columnOptions = columns.map((column) => ({ value: column.id, label: column.name }));
	$: tags = (card.tags ?? []).map((tag) => ({ name: tag }));

	let columnId = '';
	let priority = '';
	let owner = '';
	let assignedAgent = '';

	// Pola formularza sa pochodna aktualnie wybranej karty, wiec resetujemy je
	// za kazdym razem, gdy uzytkownik przelaczy sie na inna karte.
	$: if (card) {
		columnId = card.column_id;
		priority = card.priority ?? '';
		owner = card.owner ?? '';
		assignedAgent = card.assigned_agent ?? '';
	}

	const submitOwner = () => {
		const value = owner.trim();
		if (value !== (card.owner ?? '')) {
			onUpdate({ owner: value || null });
		}
	};

	const submitAssignedAgent = () => {
		const value = assignedAgent.trim();
		if (value !== (card.assigned_agent ?? '')) {
			onUpdate({ assigned_agent: value || null });
		}
	};
</script>

<div class="flex flex-col gap-2.5">
	<div class="flex flex-col">
		<label for="kanban-card-column" class="mb-0.5 text-xs text-gray-500">
			{$i18n.t('Status')}
		</label>
		<NativeSelect
			className={fieldClassName}
			bind:value={columnId}
			options={columnOptions}
			on:change={() => {
				if (columnId !== card.column_id) {
					onMove(columnId);
				}
			}}
		/>
	</div>

	<div class="flex flex-col">
		<label for="kanban-card-owner" class="mb-0.5 text-xs text-gray-500">{$i18n.t('Owner')}</label>
		<input
			id="kanban-card-owner"
			class={fieldClassName}
			type="text"
			bind:value={owner}
			placeholder={$i18n.t('Unassigned')}
			autocomplete="off"
			on:blur={submitOwner}
			on:keydown={(e) => {
				if (e.key === 'Enter') {
					e.currentTarget.blur();
				}
			}}
		/>
	</div>

	<div class="flex flex-col">
		<label for="kanban-card-agent" class="mb-0.5 text-xs text-gray-500">{$i18n.t('Agent')}</label>
		<input
			id="kanban-card-agent"
			class={fieldClassName}
			type="text"
			bind:value={assignedAgent}
			placeholder={$i18n.t('Unassigned')}
			autocomplete="off"
			on:blur={submitAssignedAgent}
			on:keydown={(e) => {
				if (e.key === 'Enter') {
					e.currentTarget.blur();
				}
			}}
		/>
	</div>

	<div class="flex flex-col">
		<label for="kanban-card-priority" class="mb-0.5 text-xs text-gray-500">
			{$i18n.t('Priority')}
		</label>
		<NativeSelect
			className={fieldClassName}
			bind:value={priority}
			options={priorityOptions}
			on:change={() => {
				onUpdate({ priority: priority || null });
			}}
		/>
	</div>

	<div class="flex flex-col">
		<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Tags')}</div>
		<Tags
			{tags}
			on:add={(e) => {
				onUpdate({ tags: [...(card.tags ?? []), e.detail] });
			}}
			on:delete={(e) => {
				onUpdate({ tags: (card.tags ?? []).filter((tag) => tag !== e.detail) });
			}}
		/>
	</div>
</div>
