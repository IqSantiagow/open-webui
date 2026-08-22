import { WEBUI_API_BASE_URL } from '$lib/constants';

export type KanbanCard = {
	id: string;
	board_id: string;
	column_id: string;
	title: string;
	description?: string | null;
	order: number;
	owner?: string | null;
	assigned_agent?: string | null;
	priority?: string | null;
	tags?: string[] | null;
	meta?: object | null;
	created_at: number;
	updated_at: number;
};

export type KanbanColumn = {
	id: string;
	board_id: string;
	name: string;
	order: number;
	created_at: number;
	updated_at: number;
	cards: KanbanCard[];
};

export type KanbanBoardItem = {
	id: string;
	user_id: string;
	folder_id?: string | null;
	name: string;
	meta?: object | null;
	card_count: number;
	created_at: number;
	updated_at: number;
};

export type KanbanBoard = {
	board: {
		id: string;
		user_id: string;
		folder_id?: string | null;
		name: string;
		meta?: object | null;
		created_at: number;
		updated_at: number;
	};
	columns: KanbanColumn[];
};

export type KanbanActivity = {
	id: string;
	card_id: string;
	actor: string;
	action: string;
	payload?: Record<string, any> | null;
	created_at: number;
};

type KanbanCardPayload = {
	column_id?: string;
	title?: string;
	description?: string | null;
	owner?: string | null;
	assigned_agent?: string | null;
	priority?: string | null;
	tags?: string[] | null;
	meta?: object | null;
};

const request = async (token: string, path: string, method: string = 'GET', body?: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/kanban${path}`, {
		method,
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail ?? err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getKanbanBoards = async (token: string): Promise<KanbanBoardItem[]> => {
	return await request(token, '/boards');
};

export const createKanbanBoard = async (
	token: string,
	name: string,
	folderId: string | null = null
): Promise<KanbanBoardItem> => {
	return await request(token, '/boards', 'POST', { name, folder_id: folderId });
};

export const updateKanbanBoard = async (
	token: string,
	boardId: string,
	fields: { name?: string; folder_id?: string | null }
): Promise<KanbanBoardItem> => {
	return await request(token, `/boards/${boardId}/update`, 'POST', fields);
};

export const deleteKanbanBoard = async (token: string, boardId: string): Promise<boolean> => {
	return await request(token, `/boards/${boardId}`, 'DELETE');
};

export const getKanbanBoard = async (
	token: string,
	boardId: string | null = null
): Promise<KanbanBoard> => {
	return await request(token, boardId ? `/board?board_id=${boardId}` : '/board');
};

export const createKanbanColumn = async (
	token: string,
	name: string,
	boardId: string | null = null
): Promise<KanbanColumn> => {
	return await request(token, boardId ? `/columns?board_id=${boardId}` : '/columns', 'POST', {
		name
	});
};

export const updateKanbanColumn = async (
	token: string,
	columnId: string,
	name: string
): Promise<KanbanColumn> => {
	return await request(token, `/columns/${columnId}/update`, 'POST', { name });
};

export const deleteKanbanColumn = async (token: string, columnId: string): Promise<boolean> => {
	return await request(token, `/columns/${columnId}`, 'DELETE');
};

export const reorderKanbanColumns = async (
	token: string,
	columnIds: string[],
	boardId: string | null = null
): Promise<KanbanColumn[]> => {
	return await request(
		token,
		boardId ? `/columns/reorder?board_id=${boardId}` : '/columns/reorder',
		'POST',
		{ column_ids: columnIds }
	);
};

export const createKanbanCard = async (
	token: string,
	card: KanbanCardPayload
): Promise<KanbanCard> => {
	return await request(token, '/cards', 'POST', card);
};

export const updateKanbanCard = async (
	token: string,
	cardId: string,
	card: KanbanCardPayload
): Promise<KanbanCard> => {
	return await request(token, `/cards/${cardId}/update`, 'POST', card);
};

export const moveKanbanCard = async (
	token: string,
	cardId: string,
	columnId: string,
	position: number | null = null
): Promise<KanbanCard> => {
	return await request(token, `/cards/${cardId}/move`, 'POST', {
		column_id: columnId,
		position
	});
};

export const deleteKanbanCard = async (token: string, cardId: string): Promise<boolean> => {
	return await request(token, `/cards/${cardId}`, 'DELETE');
};

export const getKanbanCardActivity = async (
	token: string,
	cardId: string
): Promise<KanbanActivity[]> => {
	return await request(token, `/cards/${cardId}/activity`);
};

export const createKanbanCardComment = async (
	token: string,
	cardId: string,
	text: string
): Promise<KanbanActivity> => {
	return await request(token, `/cards/${cardId}/comment`, 'POST', { text });
};
