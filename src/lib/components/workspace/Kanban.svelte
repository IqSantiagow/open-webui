<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onDestroy, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import { WEBUI_NAME, folders, socket, workspaceActions, workspaceCounts } from '$lib/stores';
	import { getFolders } from '$lib/apis/folders';
	import {
		createKanbanBoard,
		createKanbanCard,
		createKanbanCardComment,
		createKanbanColumn,
		deleteKanbanBoard,
		deleteKanbanCard,
		deleteKanbanColumn,
		getKanbanBoard,
		getKanbanBoards,
		getKanbanCardActivity,
		moveKanbanCard,
		reorderKanbanColumns,
		updateKanbanBoard,
		updateKanbanCard,
		updateKanbanColumn
	} from '$lib/apis/kanban';
	import type { KanbanActivity, KanbanBoard, KanbanBoardItem, KanbanCard } from '$lib/apis/kanban';

	import Board from './Kanban/Board.svelte';
	import BoardModal from './Kanban/BoardModal.svelte';
	import BoardSelector from './Kanban/BoardSelector.svelte';
	import CardModal from './Kanban/CardModal.svelte';
	import CardPanel from './Kanban/CardPanel.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	// Ostatnio otwarta tablica jest pamietana lokalnie, zeby powrot do zakladki
	// nie przerzucal uzytkownika na tablice domyslna.
	const SELECTED_BOARD_STORAGE_KEY = 'kanban-selected-board-id';

	let loaded = false;
	let board: KanbanBoard | null = null;
	let boards: KanbanBoardItem[] = [];
	let selectedBoardId = '';

	let query = '';
	let ownerFilter = '';

	let selectedCardId: string | null = null;
	let activity: KanbanActivity[] = [];

	let showCardModal = false;
	let showDeleteConfirm = false;
	let showBoardModal = false;
	let showBoardDeleteConfirm = false;

	// Modal tablicy sluzy zarowno do tworzenia (null), jak i edycji istniejacej.
	let editedBoard: KanbanBoardItem | null = null;

	// Sortable przestawia wezly DOM poza kontrola Svelte, wiec po kazdym przeciagnieciu
	// podbijamy wersje tablicy i wymuszamy jej pelne przerysowanie.
	let boardVersion = 0;

	$: currentBoard = boards.find((item) => item.id === selectedBoardId) ?? null;
	$: columns = board?.columns ?? [];
	$: allCards = columns.flatMap((column) => column.cards);
	$: selectedCard = allCards.find((card) => card.id === selectedCardId) ?? null;

	$: owners = [
		...new Set(
			allCards.flatMap((card) => [card.owner, card.assigned_agent].filter((value) => !!value))
		)
	].sort();

	// Filtrowanie jest czysto wizualne - karty zostaja w swoich kolumnach,
	// a ukrywamy jedynie te, ktore nie pasuja do wyszukiwania albo wlasciciela.
	$: filteredCards = Object.fromEntries(
		columns.map((column) => [
			column.id,
			column.cards.filter((card) => {
				const matchesQuery =
					!query ||
					card.title.toLowerCase().includes(query.toLowerCase()) ||
					(card.description ?? '').toLowerCase().includes(query.toLowerCase());

				const matchesOwner =
					!ownerFilter || card.owner === ownerFilter || card.assigned_agent === ownerFilter;

				return matchesQuery && matchesOwner;
			})
		])
	);

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'kanban-new-card',
				label: $i18n.t('Create'),
				onClick: () => {
					const targetColumn = columns[0];
					if (targetColumn) {
						createCardHandler(targetColumn.id, $i18n.t('New Card'));
					} else {
						toast.error($i18n.t('Add a column first'));
					}
				}
			},
			{
				id: 'kanban-new-column',
				label: $i18n.t('Add Column'),
				onClick: () => {
					createColumnHandler($i18n.t('New Column'));
				}
			},
			{
				id: 'kanban-new-board',
				label: $i18n.t('New Board'),
				onClick: () => {
					openBoardModal(null);
				}
			}
		]);
	}

	const loadBoards = async () => {
		boards = (await getKanbanBoards(localStorage.token).catch((error) => {
			toast.error(`${error}`);
			return [];
		})) as KanbanBoardItem[];

		// Jesli zapamietana tablica zniknela, wracamy na pierwsza dostepna.
		if (!boards.some((item) => item.id === selectedBoardId)) {
			selectedBoardId = boards[0]?.id ?? '';
		}

		workspaceCounts.update((counts) => ({
			...counts,
			kanban: boards.reduce((total, item) => total + item.card_count, 0)
		}));
	};

	const loadBoard = async () => {
		board = await getKanbanBoard(localStorage.token, selectedBoardId || null).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (board?.board?.id) {
			selectedBoardId = board.board.id;
			localStorage.setItem(SELECTED_BOARD_STORAGE_KEY, selectedBoardId);
		}
	};

	const selectBoardHandler = async (boardId: string) => {
		if (boardId === selectedBoardId) {
			return;
		}

		selectedBoardId = boardId;
		closePanelHandler();

		await loadBoard();
		boardVersion += 1;
	};

	const openBoardModal = (item: KanbanBoardItem | null) => {
		editedBoard = item;
		showBoardModal = true;
	};

	const submitBoardHandler = async (fields: { name: string; folder_id: string | null }) => {
		if (editedBoard) {
			const updated = await updateKanbanBoard(localStorage.token, editedBoard.id, fields).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (updated) {
				await loadBoards();
				await loadBoard();
			}
			return;
		}

		const created = await createKanbanBoard(
			localStorage.token,
			fields.name,
			fields.folder_id
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (created) {
			await loadBoards();
			await selectBoardHandler(created.id);
		}
	};

	const deleteBoardHandler = async () => {
		if (!currentBoard) {
			return;
		}

		const result = await deleteKanbanBoard(localStorage.token, currentBoard.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (result) {
			closePanelHandler();
			selectedBoardId = '';
			await loadBoards();
			await loadBoard();
			boardVersion += 1;
		}
	};

	const loadActivity = async (cardId: string) => {
		activity = await getKanbanCardActivity(localStorage.token, cardId).catch(() => []);
	};

	const selectCardHandler = async (card: KanbanCard) => {
		selectedCardId = card.id;
		await loadActivity(card.id);
	};

	const openCardHandler = async (card: KanbanCard) => {
		await selectCardHandler(card);
		showCardModal = true;
	};

	const closePanelHandler = () => {
		selectedCardId = null;
		activity = [];
	};

	const createColumnHandler = async (name: string) => {
		const column = await createKanbanColumn(
			localStorage.token,
			name,
			selectedBoardId || null
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (column) {
			await loadBoard();
		}
	};

	const renameColumnHandler = async (columnId: string, name: string) => {
		const column = await updateKanbanColumn(localStorage.token, columnId, name).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (column) {
			await loadBoard();
		}
	};

	const deleteColumnHandler = async (columnId: string) => {
		const result = await deleteKanbanColumn(localStorage.token, columnId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (result) {
			if (selectedCard?.column_id === columnId) {
				closePanelHandler();
			}
			await loadBoard();
		}
	};

	const reorderColumnsHandler = async (columnIds: string[]) => {
		const result = await reorderKanbanColumns(
			localStorage.token,
			columnIds,
			selectedBoardId || null
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (result) {
			await loadBoard();
			boardVersion += 1;
		}
	};

	const createCardHandler = async (columnId: string, title: string) => {
		const card = await createKanbanCard(localStorage.token, {
			column_id: columnId,
			title
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (card) {
			await loadBoard();
			await loadBoards();
			await selectCardHandler(card);
		}
	};

	const updateCardHandler = async (cardId: string, fields: Record<string, any>) => {
		const card = await updateKanbanCard(localStorage.token, cardId, fields).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (card) {
			await loadBoard();
			await loadActivity(cardId);
		}
	};

	const moveCardHandler = async (cardId: string, columnId: string, position: number) => {
		const card = await moveKanbanCard(localStorage.token, cardId, columnId, position).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (card) {
			await loadBoard();
			boardVersion += 1;

			if (selectedCardId === cardId) {
				await loadActivity(cardId);
			}
		}
	};

	const deleteCardHandler = async () => {
		if (!selectedCardId) {
			return;
		}

		const result = await deleteKanbanCard(localStorage.token, selectedCardId).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (result) {
			showCardModal = false;
			closePanelHandler();
			await loadBoard();
			await loadBoards();
		}
	};

	const commentHandler = async (cardId: string, text: string) => {
		const entry = await createKanbanCardComment(localStorage.token, cardId, text).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (entry) {
			await loadActivity(cardId);
		}
	};

	// Zmiany wprowadzone przez agentow przychodza socketem, dzieki czemu otwarta
	// tablica aktualizuje sie bez odswiezania strony.
	const kanbanEventHandler = async (event: { action: string; card_id?: string }) => {
		await loadBoard();
		await loadBoards();

		if (selectedCardId && event?.card_id === selectedCardId) {
			await loadActivity(selectedCardId);
		}
	};

	onMount(async () => {
		selectedBoardId = localStorage.getItem(SELECTED_BOARD_STORAGE_KEY) ?? '';

		if (($folders ?? []).length === 0) {
			const folderList = await getFolders(localStorage.token).catch(() => null);
			if (folderList) {
				folders.set(folderList);
			}
		}

		await loadBoards();
		await loadBoard();

		$socket?.off('events:kanban', kanbanEventHandler);
		$socket?.on('events:kanban', kanbanEventHandler);

		loaded = true;
	});

	onDestroy(() => {
		$socket?.off('events:kanban', kanbanEventHandler);
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Kanban')} / {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete card?')}
		on:confirm={deleteCardHandler}
	>
		<div class="truncate text-sm text-gray-500">
			{$i18n.t('This will delete')}
			<span class="font-normal">{selectedCard?.title ?? ''}</span>.
		</div>
	</DeleteConfirmDialog>

	<DeleteConfirmDialog
		bind:show={showBoardDeleteConfirm}
		title={$i18n.t('Delete board?')}
		on:confirm={deleteBoardHandler}
	>
		<div class="truncate text-sm text-gray-500">
			{$i18n.t('This will delete')}
			<span class="font-normal">{currentBoard?.name ?? ''}</span>
			{$i18n.t('with all its columns and cards')}.
		</div>
	</DeleteConfirmDialog>

	<BoardModal
		bind:show={showBoardModal}
		board={editedBoard}
		onSubmit={submitBoardHandler}
		onDelete={() => (showBoardDeleteConfirm = true)}
	/>

	{#if selectedCard}
		<CardModal
			bind:show={showCardModal}
			card={selectedCard}
			{columns}
			{activity}
			onUpdate={(fields) => updateCardHandler(selectedCard.id, fields)}
			onMove={(columnId) => moveCardHandler(selectedCard.id, columnId, 0)}
			onComment={(text) => commentHandler(selectedCard.id, text)}
		/>
	{/if}

	<div class="flex h-full min-h-0 flex-col">
		<div class="flex h-8 w-full shrink-0 items-center gap-2">
			<div class="flex shrink-0 items-center">
				<BoardSelector
					{boards}
					boardId={selectedBoardId}
					onSelect={selectBoardHandler}
					onCreate={() => openBoardModal(null)}
				/>

				{#if currentBoard}
					<Tooltip content={$i18n.t('Board Settings')}>
						<button
							class="rounded-lg bg-transparent p-1 transition hover:bg-gray-100 dark:hover:bg-gray-850"
							aria-label={$i18n.t('Board Settings')}
							on:click={() => openBoardModal(currentBoard)}
						>
							<Cog6 className="size-4" />
						</button>
					</Tooltip>
				{/if}
			</div>

			<div class="flex min-w-0 flex-1">
				<div class="ml-1 mr-3 self-center">
					<Search className="size-3.5" />
				</div>
				<input
					class="w-full rounded-r-xl bg-transparent py-1 pr-4 text-sm outline-hidden"
					bind:value={query}
					aria-label={$i18n.t('Search Cards')}
					placeholder={$i18n.t('Search Cards')}
				/>

				{#if query}
					<div class="translate-y-[0.5px] self-center rounded-l-xl bg-transparent pl-1.5">
						<button
							class="rounded-full p-0.5 transition hover:bg-gray-100 dark:hover:bg-gray-900"
							aria-label={$i18n.t('Clear search')}
							on:click={() => {
								query = '';
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>

			<div class="flex shrink-0 items-center gap-1">
				<label for="kanban-owner-filter" class="sr-only">{$i18n.t('Filter by owner')}</label>
				<select
					id="kanban-owner-filter"
					class="rounded-lg bg-transparent py-1 text-xs text-gray-600 outline-hidden dark:text-gray-400"
					bind:value={ownerFilter}
				>
					<option value="">{$i18n.t('All owners')}</option>
					{#each owners as owner}
						<option value={owner}>{owner}</option>
					{/each}
				</select>
			</div>
		</div>

		<div class="mt-1 flex min-h-0 flex-1 gap-3">
			<div class="min-w-0 flex-1">
				{#key boardVersion}
					<Board
						{columns}
						{filteredCards}
						{selectedCardId}
						onSelectCard={selectCardHandler}
						onOpenCard={openCardHandler}
						onCreateCard={createCardHandler}
						onMoveCard={moveCardHandler}
						onCreateColumn={createColumnHandler}
						onRenameColumn={renameColumnHandler}
						onDeleteColumn={deleteColumnHandler}
						onReorderColumns={reorderColumnsHandler}
					/>
				{/key}
			</div>

			{#if selectedCard}
				<div class="hidden w-80 shrink-0 md:block">
					<CardPanel
						card={selectedCard}
						{columns}
						{activity}
						onUpdate={(fields) => updateCardHandler(selectedCard.id, fields)}
						onMove={(columnId) => moveCardHandler(selectedCard.id, columnId, 0)}
						onComment={(text) => commentHandler(selectedCard.id, text)}
						onDelete={() => (showDeleteConfirm = true)}
						onExpand={() => (showCardModal = true)}
						onClose={closePanelHandler}
					/>
				</div>
			{/if}
		</div>
	</div>
{:else}
	<div class="flex h-full w-full items-center justify-center">
		<Spinner />
	</div>
{/if}
