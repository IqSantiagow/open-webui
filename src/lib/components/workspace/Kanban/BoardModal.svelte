<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import type { KanbanBoardItem } from '$lib/apis/kanban';
	import FolderDropdown from '$lib/components/automations/FolderDropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let show = false;

	// Brak tablicy oznacza tryb tworzenia nowej.
	export let board: KanbanBoardItem | null = null;

	export let onSubmit: (fields: { name: string; folder_id: string | null }) => void = () => {};
	export let onDelete: () => void = () => {};

	let name = '';
	let folderId = '';

	$: if (show) {
		name = board?.name ?? '';
		folderId = board?.folder_id ?? '';
	}

	const submitHandler = () => {
		const value = name.trim();
		if (!value) {
			return;
		}

		onSubmit({ name: value, folder_id: folderId || null });
		show = false;
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class="flex justify-between px-5 pt-4 pb-1.5 dark:text-gray-100">
			<h1 class="self-center font-primary text-lg font-medium">
				{board ? $i18n.t('Board Settings') : $i18n.t('New Board')}
			</h1>
			<button
				class="self-center"
				aria-label={$i18n.t('Close modal')}
				on:click={() => (show = false)}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex w-full flex-col px-4 pb-4 dark:text-gray-200">
			<form class="flex w-full flex-col" on:submit|preventDefault={submitHandler}>
				<div class="flex flex-col gap-2.5 px-1">
					<div class="flex w-full flex-col">
						<label for="kanban-board-name" class="mb-0.5 text-xs text-gray-500">
							{$i18n.t('Name')}
						</label>
						<input
							id="kanban-board-name"
							class="w-full rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-sm text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
							type="text"
							bind:value={name}
							placeholder={$i18n.t('Board name')}
							autocomplete="off"
							required
						/>
					</div>

					<div class="flex w-full flex-col">
						<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Folder')}</div>
						<div class="flex">
							<FolderDropdown bind:folder_id={folderId} side="bottom" />
						</div>
					</div>
				</div>

				<div class="flex items-center justify-between pt-3 text-sm font-medium">
					{#if board}
						<button
							class="flex items-center gap-1.5 rounded-lg bg-transparent px-2 py-1 text-xs font-normal text-gray-500 transition hover:bg-gray-100 hover:text-red-500 dark:hover:bg-gray-850"
							type="button"
							on:click={() => {
								show = false;
								onDelete();
							}}
						>
							<GarbageBin className="size-3.5" />
							{$i18n.t('Delete')}
						</button>
					{:else}
						<div></div>
					{/if}

					<button
						class="flex items-center gap-2 rounded-full bg-black px-3.5 py-1.5 text-sm font-medium text-white transition hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100"
						type="submit"
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</form>
		</div>
	</div>
</Modal>
