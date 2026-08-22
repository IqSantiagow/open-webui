<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import type { KanbanActivity, KanbanCard, KanbanColumn } from '$lib/apis/kanban';
	import CardActivity from './CardActivity.svelte';
	import CardProperties from './CardProperties.svelte';
	import ArrowsPointingOut from '$lib/components/icons/ArrowsPointingOut.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let card: KanbanCard;
	export let columns: KanbanColumn[] = [];
	export let activity: KanbanActivity[] = [];

	export let onUpdate: (fields: Record<string, any>) => void = () => {};
	export let onMove: (columnId: string) => void = () => {};
	export let onComment: (text: string) => void = () => {};
	export let onDelete: () => void = () => {};
	export let onExpand: () => void = () => {};
	export let onClose: () => void = () => {};

	let title = '';

	$: if (card) {
		title = card.title;
	}

	const submitTitle = () => {
		const value = title.trim();
		if (value && value !== card.title) {
			onUpdate({ title: value });
		} else {
			title = card.title;
		}
	};
</script>

<div
	class="flex h-full w-full flex-col overflow-y-auto rounded-2xl border border-gray-100 p-3 dark:border-gray-850"
>
	<div class="flex items-start gap-1">
		<textarea
			class="min-h-7 w-full resize-none bg-transparent text-sm outline-hidden dark:text-gray-100"
			rows="1"
			bind:value={title}
			aria-label={$i18n.t('Card title')}
			on:blur={submitTitle}
			on:keydown={(e) => {
				if (e.key === 'Enter') {
					e.preventDefault();
					e.currentTarget.blur();
				}
			}}
		></textarea>

		<Tooltip content={$i18n.t('Expand')}>
			<button
				class="shrink-0 rounded-lg bg-transparent p-1 transition hover:bg-gray-100 dark:hover:bg-gray-850"
				aria-label={$i18n.t('Expand')}
				on:click={onExpand}
			>
				<ArrowsPointingOut className="size-3.5" />
			</button>
		</Tooltip>

		<button
			class="shrink-0 rounded-lg bg-transparent p-1 transition hover:bg-gray-100 dark:hover:bg-gray-850"
			aria-label={$i18n.t('Close')}
			on:click={onClose}
		>
			<XMark className="size-4" />
		</button>
	</div>

	<hr class="my-2.5 border-gray-50/30 dark:border-gray-800/30" />

	<CardProperties {card} {columns} {onUpdate} {onMove} />

	<hr class="my-2.5 border-gray-50/30 dark:border-gray-800/30" />

	<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Description')}</div>
	{#if card.description}
		<div class="whitespace-pre-wrap text-xs text-gray-700 dark:text-gray-300">
			{card.description}
		</div>
	{:else}
		<button
			class="text-left text-xs text-gray-400 transition hover:text-gray-900 dark:text-gray-600 dark:hover:text-white"
			on:click={onExpand}
		>
			{$i18n.t('Add a description')}
		</button>
	{/if}

	<hr class="my-2.5 border-gray-50/30 dark:border-gray-800/30" />

	<div class="mb-1 text-xs text-gray-500">{$i18n.t('Activity')}</div>
	<CardActivity {activity} {onComment} />

	<div class="mt-3 flex justify-end">
		<button
			class="flex items-center gap-1.5 rounded-lg bg-transparent px-2 py-1 text-xs text-gray-500 transition hover:bg-gray-100 hover:text-red-500 dark:hover:bg-gray-850"
			on:click={onDelete}
		>
			<GarbageBin className="size-3.5" />
			{$i18n.t('Delete')}
		</button>
	</div>
</div>
