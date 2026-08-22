<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import type { KanbanCard } from '$lib/apis/kanban';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Bars3BottomLeft from '$lib/components/icons/Bars3BottomLeft.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let card: KanbanCard;
	export let selected = false;

	export let onSelect: (card: KanbanCard) => void = () => {};
	export let onOpen: (card: KanbanCard) => void = () => {};

	const priorityLabels: Record<string, string> = {
		high: 'High',
		medium: 'Medium',
		low: 'Low'
	};

	const priorityDotClasses: Record<string, string> = {
		high: 'bg-red-500',
		medium: 'bg-yellow-500',
		low: 'bg-gray-300 dark:bg-gray-600'
	};
</script>

<button
	class="w-full text-left rounded-xl border px-2.5 py-2 transition cursor-pointer {selected
		? 'border-gray-300 bg-gray-50/60 dark:border-gray-700 dark:bg-gray-800/40'
		: 'border-gray-100 bg-white hover:bg-gray-50/40 dark:border-gray-850 dark:bg-transparent dark:hover:bg-gray-800/40'}"
	data-id={card.id}
	aria-label={card.title}
	on:click={() => onSelect(card)}
	on:dblclick={() => onOpen(card)}
>
	<div class="flex items-start gap-1.5">
		{#if card.priority}
			<Tooltip content={$i18n.t(priorityLabels[card.priority] ?? card.priority)}>
				<span
					class="mt-1.5 size-1.5 shrink-0 rounded-full {priorityDotClasses[card.priority] ??
						'bg-gray-300 dark:bg-gray-600'}"
				></span>
			</Tooltip>
		{/if}

		<div class="min-w-0 flex-1 text-sm line-clamp-2 dark:text-gray-100">
			{card.title}
		</div>
	</div>

	<div class="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
		{#if card.assigned_agent || card.owner}
			<span class="truncate max-w-[9rem]">@{card.assigned_agent || card.owner}</span>
		{/if}

		{#if card.description}
			<Tooltip content={$i18n.t('Description')}>
				<Bars3BottomLeft className="size-3.5" />
			</Tooltip>
		{/if}

		{#each card.tags ?? [] as tag}
			<span
				class="rounded-full bg-gray-50 px-1.5 py-0.5 text-[0.6875rem] text-gray-600 dark:bg-gray-850 dark:text-gray-400"
			>
				{tag}
			</span>
		{/each}
	</div>
</button>
