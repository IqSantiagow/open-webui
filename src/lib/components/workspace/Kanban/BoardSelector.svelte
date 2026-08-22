<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { folders } from '$lib/stores';
	import { decodeString } from '$lib/utils';
	import type { KanbanBoardItem } from '$lib/apis/kanban';

	import Check from '$lib/components/icons/Check.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Select from '$lib/components/common/Select.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let boards: KanbanBoardItem[] = [];
	export let boardId = '';

	export let onSelect: (boardId: string) => void = () => {};
	export let onCreate: () => void = () => {};

	let boardSearch = '';

	const folderName = (folderId?: string | null): string => {
		const folder = (($folders ?? []) as any[]).find((item) => item.id === folderId);
		return folder ? decodeString(folder.name ?? '') : '';
	};

	$: selectedBoard = boards.find((board) => board.id === boardId);
	$: boardLabel = selectedBoard ? selectedBoard.name : $i18n.t('Select a board');

	$: normalizedSearch = boardSearch.trim().toLowerCase();
	$: filteredBoards = normalizedSearch
		? boards.filter((board) =>
				`${board.name} ${folderName(board.folder_id)}`.toLowerCase().includes(normalizedSearch)
			)
		: boards;

	// Tablice grupujemy po folderze; te bez folderu ladują w osobnej sekcji na koncu.
	$: groups = (() => {
		const grouped = new Map<string, { label: string; items: KanbanBoardItem[] }>();

		for (const board of filteredBoards) {
			const key = board.folder_id ?? '';
			const label = key ? folderName(key) || $i18n.t('Folder') : $i18n.t('No folder');

			if (!grouped.has(key)) {
				grouped.set(key, { label, items: [] });
			}
			grouped.get(key)?.items.push(board);
		}

		return [...grouped.entries()]
			.sort(([keyA], [keyB]) => {
				if (keyA === '') return 1;
				if (keyB === '') return -1;
				return grouped.get(keyA)!.label.localeCompare(grouped.get(keyB)!.label);
			})
			.map(([, group]) => group);
	})();
</script>

<Select
	value={boardId}
	items={boards.map((board) => ({ value: board.id, label: board.name }))}
	placeholder={$i18n.t('Select a board')}
	align="start"
	side="bottom"
	triggerClass="relative h-8 max-w-[14rem] flex items-center gap-1.5 px-2.5 py-1.5 bg-transparent rounded-2xl text-sm font-normal text-gray-900 transition hover:text-gray-900 dark:text-gray-100"
	contentClass="w-72 shadow-lg"
	maxHeight="20rem"
	onClose={() => {
		boardSearch = '';
	}}
>
	<svelte:fragment slot="trigger">
		<div class="inline-flex min-w-0 flex-1 truncate bg-transparent outline-hidden">
			{boardLabel}
		</div>
		<ChevronDown className="size-2.5 shrink-0" strokeWidth="2.5" />
	</svelte:fragment>

	<svelte:fragment let:selectItem>
		<div class="flex items-center gap-1.5 px-2 py-1">
			<Search className="size-3.5 shrink-0" strokeWidth="2.5" />
			<input
				bind:value={boardSearch}
				class="w-full bg-transparent text-[13px] outline-hidden"
				placeholder={$i18n.t('Search boards')}
				autocomplete="off"
				on:click|stopPropagation
			/>
		</div>

		{#each groups as group}
			<hr class="mx-1 my-0.5 border-gray-50/30 dark:border-gray-800/30" />
			<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
				{group.label}
			</div>

			{#each group.items as board (board.id)}
				<button
					type="button"
					class="flex h-[1.6875rem] w-full cursor-pointer items-center justify-between gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 {boardId ===
					board.id
						? 'text-gray-900 dark:text-gray-100'
						: 'text-gray-700 dark:text-gray-300'}"
					on:click={() => {
						selectItem({ value: board.id, label: board.name });
						boardSearch = '';
						onSelect(board.id);
					}}
				>
					<div class="flex min-w-0 items-center gap-1.5">
						<span class="min-w-0 truncate">{board.name}</span>
						<span class="shrink-0 text-[11px] text-gray-400 dark:text-gray-600">
							{board.card_count}
						</span>
					</div>
					{#if boardId === board.id}
						<Check className="size-3.5 shrink-0" strokeWidth="2" />
					{/if}
				</button>
			{/each}
		{:else}
			<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
				{$i18n.t('No results found')}
			</div>
		{/each}

		<hr class="mx-1 my-0.5 border-gray-50/30 dark:border-gray-800/30" />

		<button
			type="button"
			class="flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] text-gray-700 hover:bg-gray-50/40 hover:text-gray-900 dark:text-gray-300 dark:hover:bg-gray-800/40 dark:hover:text-gray-100"
			on:click={() => {
				boardSearch = '';
				onCreate();
			}}
		>
			<Plus className="size-3.5 shrink-0" />
			{$i18n.t('New Board')}
		</button>
	</svelte:fragment>
</Select>
