<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	dayjs.extend(relativeTime);

	import type { KanbanActivity } from '$lib/apis/kanban';
	import ArrowRight from '$lib/components/icons/ArrowRight.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let activity: KanbanActivity[] = [];
	export let showCommentInput = true;

	export let onComment: (text: string) => void = () => {};

	let commentValue = '';

	const describe = (entry: KanbanActivity): string => {
		const payload = entry.payload ?? {};

		if (entry.action === 'commented') {
			return payload.text ?? '';
		}
		if (entry.action === 'moved') {
			return $i18n.t('moved to {{column}}', { column: payload.to_column ?? '' });
		}
		if (entry.action === 'created') {
			return $i18n.t('created this card');
		}
		if (entry.action === 'updated') {
			return $i18n.t('updated {{fields}}', { fields: (payload.fields ?? []).join(', ') });
		}

		return entry.action;
	};

	const submitComment = () => {
		const text = commentValue.trim();
		if (!text) {
			return;
		}

		commentValue = '';
		onComment(text);
	};
</script>

<div class="flex flex-col gap-1.5">
	{#if activity.length === 0}
		<div class="text-xs text-gray-400 dark:text-gray-600">{$i18n.t('No activity yet')}</div>
	{/if}

	{#each activity as entry (entry.id)}
		<div class="text-xs text-gray-600 dark:text-gray-400">
			<span class="text-gray-900 dark:text-gray-200">{entry.actor}</span>
			<span>{describe(entry)}</span>
			<span class="text-gray-400 dark:text-gray-600">
				· {dayjs(entry.created_at / 1000000).fromNow()}
			</span>
		</div>
	{/each}
</div>

{#if showCommentInput}
	<div
		class="mt-2 flex items-center gap-1 rounded-lg border border-gray-100/50 bg-gray-50/40 px-2 py-1 transition-colors focus-within:border-blue-400 dark:border-white/[0.04] dark:bg-white/[0.03] dark:focus-within:border-blue-500"
	>
		<input
			class="w-full bg-transparent text-xs outline-hidden placeholder:text-gray-300 dark:text-gray-300 dark:placeholder:text-gray-700"
			type="text"
			bind:value={commentValue}
			aria-label={$i18n.t('Comment')}
			placeholder={$i18n.t('Comment')}
			autocomplete="off"
			on:keydown={(e) => {
				if (e.key === 'Enter') {
					submitComment();
				}
			}}
		/>

		<button
			class="shrink-0 rounded-lg bg-transparent p-1 transition hover:bg-gray-100 dark:hover:bg-gray-850"
			aria-label={$i18n.t('Send')}
			on:click={submitComment}
		>
			<ArrowRight className="size-3.5" />
		</button>
	</div>
{/if}
