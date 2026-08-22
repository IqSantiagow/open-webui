<script lang="ts">
	import dayjs from 'dayjs';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import type { KanbanActivity, KanbanCard, KanbanColumn } from '$lib/apis/kanban';
	import CardActivity from './CardActivity.svelte';
	import CardProperties from './CardProperties.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let show = false;

	export let card: KanbanCard;
	export let columns: KanbanColumn[] = [];
	export let activity: KanbanActivity[] = [];

	export let onUpdate: (fields: Record<string, any>) => void = () => {};
	export let onMove: (columnId: string) => void = () => {};
	export let onComment: (text: string) => void = () => {};

	let title = '';
	let description = '';

	$: if (card) {
		title = card.title;
		description = card.description ?? '';
	}

	const submitTitle = () => {
		const value = title.trim();
		if (value && value !== card.title) {
			onUpdate({ title: value });
		} else {
			title = card.title;
		}
	};

	const submitDescription = () => {
		if (description !== (card.description ?? '')) {
			onUpdate({ description });
		}
	};
</script>

<Modal size="md" bind:show>
	<div>
		<div class="flex justify-between gap-2 px-5 pt-4 pb-1.5 dark:text-gray-100">
			<textarea
				class="min-h-7 w-full resize-none self-center bg-transparent font-primary text-lg font-medium outline-hidden"
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

			<button
				class="self-center"
				aria-label={$i18n.t('Close modal')}
				on:click={() => (show = false)}
			>
				<XMark className={'size-5'} />
			</button>
		</div>

		<div class="flex w-full flex-col px-4 pb-4 dark:text-gray-200">
			<div class="flex flex-col gap-4 px-1 md:flex-row">
				<div class="flex min-w-0 flex-1 flex-col">
					<div class="mb-0.5 text-xs text-gray-500">{$i18n.t('Description')}</div>
					<textarea
						class="min-h-32 w-full resize-none rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1.5 text-sm text-gray-700 outline-hidden transition-colors focus:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:text-gray-300 dark:focus:border-blue-500"
						bind:value={description}
						aria-label={$i18n.t('Description')}
						placeholder={$i18n.t('Add a description')}
						on:blur={submitDescription}
					></textarea>

					<div class="mt-4 mb-1 text-xs text-gray-500">{$i18n.t('Activity')}</div>
					<CardActivity {activity} {onComment} />
				</div>

				<div class="w-full shrink-0 md:w-56">
					<CardProperties {card} {columns} {onUpdate} {onMove} />

					<div class="mt-2.5 text-[0.6875rem] text-gray-400 dark:text-gray-600">
						{$i18n.t('Created')}
						{dayjs(card.created_at / 1000000).format('YYYY-MM-DD HH:mm')}
					</div>
				</div>
			</div>
		</div>
	</div>
</Modal>
