<script lang="ts">
	import { getContext } from 'svelte';
	import { slide } from 'svelte/transition';

	import XMark from '$lib/components/icons/XMark.svelte';

	import type {
		PendingQuestionAnswer,
		PendingQuestionEntry,
		PendingQuestionItem
	} from '$lib/stores';

	const i18n = getContext('i18n');

	// Interactive mode: a question round that is still waiting for the user.
	export let entry: PendingQuestionEntry | null = null;

	// Read-only mode: a question round that was already persisted on the message.
	export let round: {
		id?: string;
		questions?: PendingQuestionItem[];
		answers?: PendingQuestionAnswer[];
		cancelled?: boolean;
		reason?: string;
	} | null = null;

	export let readonly = false;

	type Selection = {
		answer: string;
		was_custom: boolean;
		option_index: number | null;
	};

	let selections: Record<string, Selection> = {};
	let customValues: Record<string, string> = {};
	let customSelected: Record<string, boolean> = {};
	let activeIndex = 0;
	let submitted = false;

	$: questions = (entry?.questions ?? round?.questions ?? []) as PendingQuestionItem[];
	$: activeQuestion = questions[activeIndex] ?? null;
	$: answeredCount = questions.filter((question) => selections[question.id] !== undefined).length;
	$: allAnswered = questions.length > 0 && answeredCount === questions.length;

	// Reactive statements are flushed asynchronously, so callers that answer and
	// submit within the same tick need a directly computed check.
	const isComplete = (): boolean => {
		return (
			questions.length > 0 && questions.every((question) => selections[question.id] !== undefined)
		);
	};

	const answerOf = (questionId: string): PendingQuestionAnswer | null => {
		return (round?.answers ?? []).find((answer) => answer.id === questionId) ?? null;
	};

	// After answering, jump to the first question that is still open so a multi
	// question round can be completed without extra clicks on the tabs.
	const focusNextUnanswered = () => {
		const nextIndex = questions.findIndex((question) => selections[question.id] === undefined);
		if (nextIndex !== -1) {
			activeIndex = nextIndex;
		}
	};

	const selectOption = (question: PendingQuestionItem, optionIndex: number) => {
		const option = (question.options ?? [])[optionIndex];
		if (!option || submitted) {
			return;
		}

		customSelected[question.id] = false;
		customValues[question.id] = '';
		selections[question.id] = {
			answer: option.label,
			was_custom: false,
			option_index: optionIndex
		};

		customSelected = customSelected;
		selections = selections;
		focusNextUnanswered();
	};

	const selectCustom = (question: PendingQuestionItem) => {
		if (submitted) {
			return;
		}

		customSelected[question.id] = true;
		delete selections[question.id];

		customSelected = customSelected;
		selections = selections;
	};

	const setCustomAnswer = (question: PendingQuestionItem, value: string) => {
		customValues[question.id] = value;

		if (value.trim() === '') {
			delete selections[question.id];
		} else {
			selections[question.id] = {
				answer: value.trim(),
				was_custom: true,
				option_index: null
			};
		}

		selections = selections;
	};

	const collectAnswers = (): PendingQuestionAnswer[] => {
		return questions
			.filter((question) => selections[question.id] !== undefined)
			.map((question) => ({
				id: question.id,
				answer: selections[question.id].answer,
				was_custom: selections[question.id].was_custom,
				option_index: selections[question.id].option_index
			}));
	};

	const submitHandler = () => {
		if (submitted || !entry || !isComplete()) {
			return;
		}

		submitted = true;
		entry.respond({ cancelled: false, reason: '', answers: collectAnswers() });
	};

	// Called by the chat input, which takes over answering while a question is open:
	// whatever the user typed becomes the custom answer for the active question.
	export const submitFromInput = (text: string): boolean => {
		if (submitted || !entry || !activeQuestion) {
			return false;
		}

		const value = (text ?? '').trim();
		if (value !== '') {
			customSelected[activeQuestion.id] = true;
			customSelected = customSelected;
			setCustomAnswer(activeQuestion, value);
		}

		if (isComplete()) {
			submitHandler();
		} else {
			focusNextUnanswered();
		}

		return true;
	};

	const skipHandler = () => {
		if (submitted || !entry) {
			return;
		}

		submitted = true;
		entry.respond({ cancelled: true, reason: 'skipped', answers: collectAnswers() });
	};
</script>

{#if questions.length > 0}
	<div
		class="mb-2 w-full overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-lg dark:border-gray-850 dark:bg-gray-900"
		transition:slide={{ duration: 200 }}
	>
		{#if readonly}
			<!-- Persisted question round: questions with the answers that were given -->
			<div class="px-4 py-3">
				<div class="mb-2 text-xs text-gray-400 dark:text-gray-600">
					{$i18n.t('Assistant question')}
				</div>

				<div class="space-y-2.5">
					{#each questions as question (question.id)}
						{@const answer = answerOf(question.id)}
						<div>
							<div class="text-sm text-gray-700 dark:text-gray-300">{question.question}</div>
							<div class="mt-0.5 text-sm">
								{#if answer}
									<span class="text-gray-900 dark:text-gray-100">{answer.answer}</span>
									{#if answer.was_custom}
										<span class="ml-1 text-xs text-gray-400 dark:text-gray-600">
											({$i18n.t('custom answer')})
										</span>
									{/if}
								{:else if round?.reason === 'timeout' || round?.reason === 'disconnected'}
									<span class="text-gray-400 dark:text-gray-600">
										{$i18n.t('No answer (timed out)')}
									</span>
								{:else}
									<span class="text-gray-400 dark:text-gray-600">{$i18n.t('Skipped')}</span>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{:else}
			<!-- Tabs: one tab per question, so a whole round fits into one panel -->
			<div class="flex items-center gap-1 border-b border-gray-100 px-2 pt-2 dark:border-gray-850">
				{#each questions as question, questionIdx (question.id)}
					<button
						type="button"
						class="flex items-center gap-1.5 border-b-2 px-2.5 pb-2 text-sm transition {activeIndex ===
						questionIdx
							? 'border-gray-900 text-gray-900 dark:border-white dark:text-white'
							: 'border-transparent text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300'}"
						on:click={() => (activeIndex = questionIdx)}
					>
						<span class="max-w-40 truncate">
							{question.header ? question.header : `${$i18n.t('Question')} ${questionIdx + 1}`}
						</span>
						{#if selections[question.id] !== undefined}
							<span class="size-1.5 rounded-full bg-gray-900 dark:bg-white"></span>
						{/if}
					</button>
				{/each}

				<button
					type="button"
					class="ml-auto mb-1.5 rounded-lg p-1 text-gray-400 transition hover:bg-gray-50 hover:text-gray-600 dark:hover:bg-gray-850 dark:hover:text-gray-300"
					aria-label={$i18n.t('Skip')}
					disabled={submitted}
					on:click={skipHandler}
				>
					<XMark className="size-4" />
				</button>
			</div>

			{#if activeQuestion}
				<div class="px-4 py-3">
					<div class="mb-2 text-sm font-medium text-gray-900 dark:text-gray-100">
						{activeQuestion.question}
					</div>

					<div class="flex flex-col gap-0.5">
						{#each activeQuestion.options ?? [] as option, optionIdx}
							<button
								type="button"
								class="flex w-full items-start gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-gray-50 dark:hover:bg-gray-850 {selections[
									activeQuestion.id
								]?.option_index === optionIdx
									? 'bg-gray-50 dark:bg-gray-850'
									: ''}"
								disabled={submitted}
								on:click={() => selectOption(activeQuestion, optionIdx)}
							>
								<span
									class="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border {selections[
										activeQuestion.id
									]?.option_index === optionIdx
										? 'border-gray-900 dark:border-white'
										: 'border-gray-300 dark:border-gray-600'}"
								>
									{#if selections[activeQuestion.id]?.option_index === optionIdx}
										<span class="size-2 rounded-full bg-gray-900 dark:bg-white"></span>
									{/if}
								</span>

								<span class="min-w-0">
									<span class="block text-sm text-gray-900 dark:text-gray-100">{option.label}</span>
									{#if option.description}
										<span class="block text-xs text-gray-500 dark:text-gray-400">
											{option.description}
										</span>
									{/if}
								</span>
							</button>
						{/each}

						{#if activeQuestion.allow_free_text ?? true}
							<button
								type="button"
								class="flex w-full items-start gap-3 rounded-xl px-3 py-2 text-left transition hover:bg-gray-50 dark:hover:bg-gray-850 {customSelected[
									activeQuestion.id
								]
									? 'bg-gray-50 dark:bg-gray-850'
									: ''}"
								disabled={submitted}
								on:click={() => selectCustom(activeQuestion)}
							>
								<span
									class="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full border {customSelected[
										activeQuestion.id
									]
										? 'border-gray-900 dark:border-white'
										: 'border-gray-300 dark:border-gray-600'}"
								>
									{#if customSelected[activeQuestion.id]}
										<span class="size-2 rounded-full bg-gray-900 dark:bg-white"></span>
									{/if}
								</span>

								<span class="text-sm text-gray-900 dark:text-gray-100">
									{(activeQuestion.options ?? []).length > 0
										? $i18n.t('Other')
										: $i18n.t('Your answer')}
								</span>
							</button>

							{#if customSelected[activeQuestion.id] || (activeQuestion.options ?? []).length === 0}
								<input
									class="mt-1 w-full rounded-xl bg-gray-50 px-3 py-2 text-sm outline-hidden dark:bg-gray-850 dark:text-gray-100"
									placeholder={$i18n.t('Your answer')}
									value={customValues[activeQuestion.id] ?? ''}
									disabled={submitted}
									on:input={(e) => setCustomAnswer(activeQuestion, e.currentTarget.value)}
									on:keydown={(e) => {
										if (e.key === 'Enter') {
											e.preventDefault();
											if (allAnswered) {
												submitHandler();
											} else {
												focusNextUnanswered();
											}
										}
									}}
								/>
							{/if}
						{/if}
					</div>
				</div>
			{/if}

			<div
				class="flex items-center justify-between border-t border-gray-100 px-4 py-2 dark:border-gray-850"
			>
				<span class="text-xs text-gray-400 dark:text-gray-600">
					{answeredCount}/{questions.length}
				</span>

				<button
					type="button"
					class="rounded-lg bg-black px-3.5 py-1.5 text-sm font-medium text-white transition disabled:opacity-50 dark:bg-white dark:text-black"
					disabled={submitted || !allAnswered}
					on:click={submitHandler}
				>
					{$i18n.t('Submit answers')}
				</button>
			</div>
		{/if}
	</div>
{/if}
