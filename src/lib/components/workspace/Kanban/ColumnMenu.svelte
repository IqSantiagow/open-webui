<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	export let show = false;

	export let renameHandler: Function;
	export let addCardHandler: Function;
	export let deleteHandler: Function;
</script>

<Dropdown bind:show>
	<Tooltip content={$i18n.t('More')}>
		<slot />
	</Tooltip>

	<div slot="content">
		<DropdownMenu className="min-w-[170px]">
			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
				draggable="false"
				on:click={() => {
					addCardHandler();
					show = false;
				}}
			>
				<Plus className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Add Card')}</div>
			</button>

			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
				draggable="false"
				on:click={() => {
					renameHandler();
					show = false;
				}}
			>
				<Pencil className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Rename')}</div>
			</button>

			<hr class="border-gray-50 dark:border-gray-850/30 mx-1 my-0.5" />

			<button
				class="select-none flex h-[1.6875rem] w-full cursor-pointer items-center gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:text-gray-900 dark:hover:text-gray-100"
				draggable="false"
				on:click={() => {
					deleteHandler();
					show = false;
				}}
			>
				<GarbageBin className="size-3.5" />
				<div class="flex items-center">{$i18n.t('Delete')}</div>
			</button>
		</DropdownMenu>
	</div>
</Dropdown>
