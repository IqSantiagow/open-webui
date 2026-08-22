<script lang="ts">
	import Sortable from 'sortablejs';
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import type { KanbanCard, KanbanColumn } from '$lib/apis/kanban';
	import Card from './Card.svelte';
	import ColumnMenu from './ColumnMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let column: KanbanColumn;
	export let cards: KanbanCard[] = [];
	export let selectedCardId: string | null = null;

	export let onSelectCard: (card: KanbanCard) => void = () => {};
	export let onOpenCard: (card: KanbanCard) => void = () => {};
	export let onCreateCard: (columnId: string, title: string) => void = () => {};
	export let onMoveCard: (cardId: string, columnId: string, position: number) => void = () => {};
	export let onRenameColumn: (columnId: string, name: string) => void = () => {};
	export let onDeleteColumn: (columnId: string) => void = () => {};

	// Sortable nie dostarcza typow, wiec opisujemy tylko te pola zdarzenia, ktorych uzywamy.
	type SortableEvent = {
		item: HTMLElement;
		from: HTMLElement;
		to: HTMLElement;
		oldIndex?: number;
		newIndex?: number;
	};

	let cardListElement: HTMLDivElement;
	let sortable: Sortable | null = null;

	let showMenu = false;

	let renaming = false;
	let renameValue = '';
	let renameElement: HTMLInputElement | null = null;

	let composing = false;
	let composeValue = '';
	let composeElement: HTMLTextAreaElement | null = null;

	/**
	 * Sortable przesuwa wezly DOM samodzielnie, co kloci sie z renderowaniem listy
	 * przez Svelte. Cofamy wiec zmiane w DOM i pozwalamy przerysowac liste dopiero
	 * po aktualizacji stanu w komponencie nadrzednym.
	 */
	const revertDomMove = (event: SortableEvent) => {
		const { item, from, oldIndex } = event;
		const referenceNode = from.children[oldIndex ?? 0] ?? null;
		from.insertBefore(item, referenceNode);
	};

	const initSortable = () => {
		if (!cardListElement || sortable) {
			return;
		}

		sortable = new Sortable(cardListElement, {
			group: 'kanban-cards',
			animation: 150,
			draggable: '[data-id]',
			onEnd: (event: SortableEvent) => {
				const cardId = event.item.dataset.id;
				const targetColumnId = event.to.dataset.columnId;

				const position = event.newIndex ?? 0;

				revertDomMove(event);

				if (!cardId || !targetColumnId) {
					return;
				}

				if (event.from === event.to && event.oldIndex === event.newIndex) {
					return;
				}

				onMoveCard(cardId, targetColumnId, position);
			}
		});
	};

	const startRename = async () => {
		renameValue = column.name;
		renaming = true;

		await tick();
		renameElement?.focus();
	};

	const submitRename = () => {
		const name = renameValue.trim();
		renaming = false;

		if (name && name !== column.name) {
			onRenameColumn(column.id, name);
		}
	};

	const startCompose = async () => {
		composing = true;
		composeValue = '';

		await tick();
		composeElement?.focus();
	};

	const submitCompose = () => {
		const title = composeValue.trim();
		composing = false;
		composeValue = '';

		if (title) {
			onCreateCard(column.id, title);
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

<div class="flex max-h-full w-72 shrink-0 flex-col self-start" data-id={column.id}>
	<div class="flex h-7 items-center gap-1 px-1">
		<div class="kanban-column-handle flex min-w-0 flex-1 cursor-grab items-center gap-1.5">
			{#if renaming}
				<input
					class="w-full rounded-lg bg-transparent text-sm outline-hidden dark:text-gray-100"
					bind:this={renameElement}
					bind:value={renameValue}
					aria-label={$i18n.t('Column name')}
					on:blur={submitRename}
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							submitRename();
						} else if (e.key === 'Escape') {
							renaming = false;
						}
					}}
				/>
			{:else}
				<span class="truncate text-sm dark:text-gray-100">{column.name}</span>
				<span class="text-xs text-gray-400 dark:text-gray-600">{cards.length}</span>
			{/if}
		</div>

		<ColumnMenu
			bind:show={showMenu}
			renameHandler={startRename}
			addCardHandler={startCompose}
			deleteHandler={() => onDeleteColumn(column.id)}
		>
			<button
				class="rounded-lg bg-transparent p-1 transition hover:bg-gray-100 dark:hover:bg-gray-850"
				aria-label={$i18n.t('More')}
			>
				<EllipsisHorizontal className="size-4" />
			</button>
		</ColumnMenu>
	</div>

	<div
		class="mt-1 flex min-h-24 flex-col gap-1.5 overflow-y-auto rounded-xl p-1"
		data-column-id={column.id}
		bind:this={cardListElement}
	>
		{#each cards as card (card.id)}
			<Card
				{card}
				selected={selectedCardId === card.id}
				onSelect={onSelectCard}
				onOpen={onOpenCard}
			/>
		{/each}
	</div>

	{#if composing}
		<div class="px-1 pb-1">
			<textarea
				class="w-full resize-none rounded-xl border border-gray-100 bg-white px-2.5 py-2 text-sm outline-hidden placeholder:text-gray-300 dark:border-gray-850 dark:bg-transparent dark:text-gray-100 dark:placeholder:text-gray-700"
				rows="2"
				bind:this={composeElement}
				bind:value={composeValue}
				aria-label={$i18n.t('Card title')}
				placeholder={$i18n.t('Card title')}
				on:blur={submitCompose}
				on:keydown={(e) => {
					if (e.key === 'Enter' && !e.shiftKey) {
						e.preventDefault();
						submitCompose();
					} else if (e.key === 'Escape') {
						composing = false;
						composeValue = '';
					}
				}}
			></textarea>
		</div>
	{:else}
		<button
			class="mx-1 mb-1 flex items-center gap-1.5 rounded-xl px-2 py-1.5 text-xs text-gray-500 transition hover:bg-gray-50/40 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800/40 dark:hover:text-white"
			on:click={startCompose}
		>
			<Plus className="size-3.5" />
			{$i18n.t('Add Card')}
		</button>
	{/if}
</div>
