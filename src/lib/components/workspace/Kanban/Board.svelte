<script lang="ts">
	import Sortable from 'sortablejs';
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import type { KanbanCard, KanbanColumn } from '$lib/apis/kanban';
	import Column from './Column.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let columns: KanbanColumn[] = [];
	export let filteredCards: Record<string, KanbanCard[]> = {};
	export let selectedCardId: string | null = null;

	export let onSelectCard: (card: KanbanCard) => void = () => {};
	export let onOpenCard: (card: KanbanCard) => void = () => {};
	export let onCreateCard: (columnId: string, title: string) => void = () => {};
	export let onMoveCard: (cardId: string, columnId: string, position: number) => void = () => {};
	export let onCreateColumn: (name: string) => void = () => {};
	export let onRenameColumn: (columnId: string, name: string) => void = () => {};
	export let onDeleteColumn: (columnId: string) => void = () => {};
	export let onReorderColumns: (columnIds: string[]) => void = () => {};

	// Sortable nie dostarcza typow, wiec opisujemy tylko te pola zdarzenia, ktorych uzywamy.
	type SortableEvent = {
		item: HTMLElement;
		from: HTMLElement;
		to: HTMLElement;
		oldIndex?: number;
		newIndex?: number;
	};

	let boardElement: HTMLDivElement;
	let sortable: Sortable | null = null;

	let composing = false;
	let composeValue = '';
	let composeElement: HTMLInputElement | null = null;

	/**
	 * Tak jak przy kartach: cofamy przesuniecie w DOM zrobione przez Sortable,
	 * zeby lista kolumn pozostala pod kontrola Svelte.
	 */
	const revertDomMove = (event: SortableEvent) => {
		const { item, from, oldIndex } = event;
		const referenceNode = from.children[oldIndex ?? 0] ?? null;
		from.insertBefore(item, referenceNode);
	};

	const initSortable = () => {
		if (!boardElement || sortable) {
			return;
		}

		sortable = new Sortable(boardElement, {
			animation: 150,
			draggable: '[data-id]',
			handle: '.kanban-column-handle',
			onEnd: (event: SortableEvent) => {
				const oldIndex = event.oldIndex ?? 0;
				const newIndex = event.newIndex ?? 0;

				revertDomMove(event);

				if (oldIndex === newIndex) {
					return;
				}

				const columnIds = columns.map((column) => column.id);
				const [movedId] = columnIds.splice(oldIndex, 1);
				columnIds.splice(newIndex, 0, movedId);

				onReorderColumns(columnIds);
			}
		});
	};

	const startCompose = async () => {
		composing = true;
		composeValue = '';

		await tick();
		composeElement?.focus();
	};

	const submitCompose = () => {
		const name = composeValue.trim();
		composing = false;
		composeValue = '';

		if (name) {
			onCreateColumn(name);
		}
	};

	onMount(() => {
		initSortable();
	});

	onDestroy(() => {
		sortable?.destroy();
		sortable = null;
	});
</script>

<div class="flex h-full min-h-0 w-full gap-2 overflow-x-auto pb-2" bind:this={boardElement}>
	{#each columns as column (column.id)}
		<Column
			{column}
			cards={filteredCards[column.id] ?? []}
			{selectedCardId}
			{onSelectCard}
			{onOpenCard}
			{onCreateCard}
			{onMoveCard}
			{onRenameColumn}
			{onDeleteColumn}
		/>
	{/each}

	<div class="w-56 shrink-0 pt-0.5">
		{#if composing}
			<input
				class="w-full rounded-xl border border-gray-100 bg-white px-2.5 py-1.5 text-sm outline-hidden placeholder:text-gray-300 dark:border-gray-850 dark:bg-transparent dark:text-gray-100 dark:placeholder:text-gray-700"
				bind:this={composeElement}
				bind:value={composeValue}
				aria-label={$i18n.t('Column name')}
				placeholder={$i18n.t('Column name')}
				on:blur={submitCompose}
				on:keydown={(e) => {
					if (e.key === 'Enter') {
						submitCompose();
					} else if (e.key === 'Escape') {
						composing = false;
						composeValue = '';
					}
				}}
			/>
		{:else}
			<button
				class="flex w-full items-center gap-1.5 rounded-xl px-2 py-1.5 text-xs text-gray-500 transition hover:bg-gray-50/40 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800/40 dark:hover:text-white"
				on:click={startCompose}
			>
				<Plus className="size-3.5" />
				{$i18n.t('Add Column')}
			</button>
		{/if}
	</div>
</div>
