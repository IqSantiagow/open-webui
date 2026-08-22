"""
Built-in kanban board tools for Open WebUI.

Pozwalaja modelom (agentom) czytac i modyfikowac tablice kanban uzytkownika.
Kazda operacja zapisuje wpis aktywnosci z nazwa aktora, dzieki czemu wlasciciel
tablicy widzi kto wprowadzil dana zmiane.

IMPORTANT: DO NOT IMPORT THIS MODULE DIRECTLY IN OTHER PARTS OF THE CODEBASE.
"""

import json
import logging
from typing import Optional

log = logging.getLogger(__name__)


####################
# Helpers
####################


async def _resolve_board(user_id: str, board: Optional[str] = None):
    """
    Ustala tablice, na ktorej pracuje agent. Bez podanej nazwy uzywamy tablicy
    domyslnej, a podana wartosc dopasowujemy po identyfikatorze albo nazwie.
    """
    from open_webui.models.kanban import Kanban

    if not board:
        return await Kanban.get_or_create_default_board(user_id)

    boards = await Kanban.get_boards_by_user_id(user_id)

    for item in boards:
        if item.id == board:
            return item

    normalized_name = board.strip().lower()
    for item in boards:
        if item.name.lower() == normalized_name:
            return item

    return None


async def _get_board_context(user_id: str, board: Optional[str] = None):
    """
    Zwraca wybrana tablice uzytkownika razem z lista jej kolumn.
    """
    from open_webui.models.kanban import Kanban

    resolved_board = await _resolve_board(user_id, board)
    if not resolved_board:
        return None, []

    columns = await Kanban.get_columns_by_board_id(resolved_board.id)
    return resolved_board, columns


def _resolve_column(columns: list, column: str):
    """
    Pozwala wskazac kolumne po identyfikatorze albo po nazwie
    (bez rozroznienia wielkosci liter).
    """
    for item in columns:
        if item.id == column:
            return item

    normalized_name = column.strip().lower()
    for item in columns:
        if item.name.lower() == normalized_name:
            return item

    return None


def _resolve_actor(user: dict, metadata: Optional[dict]) -> str:
    """
    Ustala nazwe aktora zapisywana w aktywnosci karty. Dla wywolan z czatu jest to
    identyfikator modelu (agenta), a gdy go brakuje - nazwa uzytkownika.
    """
    metadata = metadata or {}
    model = metadata.get('model')
    model_id = metadata.get('model_id') or (model.get('id') if isinstance(model, dict) else None)

    if model_id:
        return str(model_id)

    return user.get('name') or user.get('id') or 'agent'


def _card_dict(card, column_name: str, board_name: Optional[str] = None) -> dict:
    return {
        'id': card.id,
        'title': card.title,
        'description': card.description,
        'board': board_name,
        'column': column_name,
        'owner': card.owner,
        'assigned_agent': card.assigned_agent,
        'priority': card.priority,
        'tags': card.tags or [],
        'updated_at': card.updated_at,
    }


async def _notify_change(user_id: str, action: str, payload: dict) -> None:
    from open_webui.routers.kanban import notify_board_change

    await notify_board_change(user_id, action, payload)


async def _get_owned_card(user_id: str, card_id: str):
    """
    Zwraca karte tylko wtedy, gdy nalezy do dowolnej tablicy tego uzytkownika.
    """
    from open_webui.models.kanban import Kanban

    card = await Kanban.get_card_by_id(card_id)
    if not card:
        return None

    boards = await Kanban.get_boards_by_user_id(user_id)
    if card.board_id not in {item.id for item in boards}:
        return None

    return card


####################
# Tools
####################


async def kanban_list_boards(__user__: dict = None) -> str:
    """
    List the user's kanban boards. Use this first when the user mentions a specific board.

    :return: JSON list of boards with id, name, folder_id and card count
    """
    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.kanban import Kanban

        user_id = __user__.get('id')
        boards = await Kanban.get_boards_by_user_id(user_id)
        if not boards:
            await Kanban.get_or_create_default_board(user_id)
            boards = await Kanban.get_boards_by_user_id(user_id)

        return json.dumps(
            {
                'boards': [
                    {
                        'id': item.id,
                        'name': item.name,
                        'folder_id': item.folder_id,
                        'card_count': item.card_count,
                    }
                    for item in boards
                ],
                'default_board': boards[0].name if boards else None,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'kanban_list_boards error: {e}')
        return json.dumps({'error': str(e)})


async def kanban_list_cards(
    board: Optional[str] = None,
    column: Optional[str] = None,
    owner: Optional[str] = None,
    tag: Optional[str] = None,
    query: Optional[str] = None,
    count: int = 50,
    __user__: dict = None,
) -> str:
    """
    List cards from one of the user's kanban boards.

    :param board: Optional board name or ID; defaults to the user's first board
    :param column: Optional column name or ID filter (e.g. "In Progress")
    :param owner: Optional owner or assigned agent filter
    :param tag: Optional tag filter
    :param query: Optional text search in card title and description
    :param count: Maximum number of cards to return (default: 50)
    :return: JSON list of cards with id, title, column, owner, priority and tags
    """
    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.kanban import Kanban

        user_id = __user__.get('id')
        resolved_board, columns = await _get_board_context(user_id, board)
        if not resolved_board:
            return json.dumps({'error': f'Board "{board}" not found'})

        column_names = {item.id: item.name for item in columns}

        column_id = None
        if column:
            target_column = _resolve_column(columns, column)
            if not target_column:
                return json.dumps({'error': f'Column "{column}" not found'})
            column_id = target_column.id

        cards = await Kanban.search_cards(
            resolved_board.id,
            query=query,
            column_id=column_id,
            owner=owner,
            tag=tag,
            limit=count,
        )

        return json.dumps(
            {
                'board': resolved_board.name,
                'columns': [item.name for item in columns],
                'cards': [
                    _card_dict(card, column_names.get(card.column_id, ''), resolved_board.name) for card in cards
                ],
                'total': len(cards),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'kanban_list_cards error: {e}')
        return json.dumps({'error': str(e)})


async def kanban_create_card(
    title: str,
    column: str,
    board: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[list[str]] = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Create a new card on one of the user's kanban boards.

    :param title: Short card title
    :param column: Target column name or ID (e.g. "Backlog")
    :param board: Optional board name or ID; defaults to the user's first board
    :param description: Optional markdown description of the task
    :param priority: Optional priority: "low", "medium" or "high"
    :param tags: Optional list of tags
    :return: JSON with the created card details
    """
    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.kanban import PRIORITIES, Kanban, KanbanCardForm

        user_id = __user__.get('id')
        resolved_board, columns = await _get_board_context(user_id, board)
        if not resolved_board:
            return json.dumps({'error': f'Board "{board}" not found'})

        target_column = _resolve_column(columns, column)
        if not target_column:
            return json.dumps({'error': f'Column "{column}" not found'})

        if priority is not None and priority not in PRIORITIES:
            return json.dumps({'error': f'Priority must be one of: {", ".join(PRIORITIES)}'})

        actor = _resolve_actor(__user__, __metadata__)
        card = await Kanban.insert_card(
            resolved_board.id,
            KanbanCardForm(
                column_id=target_column.id,
                title=title,
                description=description,
                assigned_agent=actor,
                priority=priority,
                tags=tags,
            ),
        )

        await Kanban.insert_activity(card.id, actor, 'created', {'title': card.title})
        await _notify_change(user_id, 'card.created', {'card_id': card.id})

        return json.dumps(
            {'status': 'success', **_card_dict(card, target_column.name, resolved_board.name)},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'kanban_create_card error: {e}')
        return json.dumps({'error': str(e)})


async def kanban_update_card(
    card_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[list[str]] = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Update fields of an existing kanban card. Only the provided fields are changed.

    :param card_id: The ID of the card to update
    :param title: New card title
    :param description: New markdown description
    :param priority: New priority: "low", "medium" or "high"
    :param tags: New list of tags (replaces the current list)
    :return: JSON with the updated card details
    """
    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.kanban import PRIORITIES, Kanban, KanbanCardUpdateForm

        user_id = __user__.get('id')
        card = await _get_owned_card(user_id, card_id)
        if not card:
            return json.dumps({'error': 'Card not found'})

        card_board = await Kanban.get_board_by_id(card.board_id)
        columns = await Kanban.get_columns_by_board_id(card.board_id)
        column_names = {item.id: item.name for item in columns}

        if priority is not None and priority not in PRIORITIES:
            return json.dumps({'error': f'Priority must be one of: {", ".join(PRIORITIES)}'})

        fields = {
            key: value
            for key, value in (
                ('title', title),
                ('description', description),
                ('priority', priority),
                ('tags', tags),
            )
            if value is not None
        }
        if not fields:
            return json.dumps({'error': 'No fields to update'})

        updated_card = await Kanban.update_card_by_id(card_id, KanbanCardUpdateForm(**fields))

        actor = _resolve_actor(__user__, __metadata__)
        await Kanban.insert_activity(card_id, actor, 'updated', {'fields': list(fields.keys())})
        await _notify_change(user_id, 'card.updated', {'card_id': card_id})

        return json.dumps(
            {
                'status': 'success',
                **_card_dict(
                    updated_card,
                    column_names.get(updated_card.column_id, ''),
                    card_board.name if card_board else None,
                ),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'kanban_update_card error: {e}')
        return json.dumps({'error': str(e)})


async def kanban_move_card(
    card_id: str,
    column: str,
    position: Optional[int] = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Move a kanban card to another column, optionally at a specific position.

    :param card_id: The ID of the card to move
    :param column: Target column name or ID (e.g. "Done")
    :param position: Optional zero-based position within the target column (default: last)
    :return: JSON with the moved card details
    """
    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.kanban import Kanban

        user_id = __user__.get('id')
        card = await _get_owned_card(user_id, card_id)
        if not card:
            return json.dumps({'error': 'Card not found'})

        # Karty przenosimy tylko w obrebie tablicy, do ktorej naleza.
        card_board = await Kanban.get_board_by_id(card.board_id)
        columns = await Kanban.get_columns_by_board_id(card.board_id)
        target_column = _resolve_column(columns, column)
        if not target_column:
            return json.dumps({'error': f'Column "{column}" not found'})

        moved_card = await Kanban.move_card_by_id(card_id, target_column.id, position)

        actor = _resolve_actor(__user__, __metadata__)
        if card.column_id != target_column.id:
            await Kanban.insert_activity(card_id, actor, 'moved', {'to_column': target_column.name})
        await _notify_change(user_id, 'card.moved', {'card_id': card_id})

        return json.dumps(
            {
                'status': 'success',
                **_card_dict(moved_card, target_column.name, card_board.name if card_board else None),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'kanban_move_card error: {e}')
        return json.dumps({'error': str(e)})


async def kanban_comment(
    card_id: str,
    text: str,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Add a comment to a kanban card. Use this to report progress or findings on a task.

    :param card_id: The ID of the card to comment on
    :param text: The comment text
    :return: JSON with the created comment details
    """
    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.kanban import Kanban

        user_id = __user__.get('id')
        card = await _get_owned_card(user_id, card_id)
        if not card:
            return json.dumps({'error': 'Card not found'})

        actor = _resolve_actor(__user__, __metadata__)
        activity = await Kanban.insert_activity(card_id, actor, 'commented', {'text': text})
        await _notify_change(user_id, 'card.commented', {'card_id': card_id})

        return json.dumps(
            {
                'status': 'success',
                'id': activity.id,
                'card_id': card_id,
                'actor': actor,
                'created_at': activity.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'kanban_comment error: {e}')
        return json.dumps({'error': str(e)})


async def kanban_card_activity(
    card_id: str,
    count: int = 20,
    __user__: dict = None,
) -> str:
    """
    Read the activity log and comments of a kanban card.

    :param card_id: The ID of the card
    :param count: Maximum number of activity entries to return (default: 20)
    :return: JSON list of activity entries with actor, action and payload
    """
    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.kanban import Kanban

        user_id = __user__.get('id')
        card = await _get_owned_card(user_id, card_id)
        if not card:
            return json.dumps({'error': 'Card not found'})

        entries = await Kanban.get_activity_by_card_id(card_id, limit=count)

        return json.dumps(
            {
                'card_id': card_id,
                'activity': [
                    {
                        'actor': entry.actor,
                        'action': entry.action,
                        'payload': entry.payload,
                        'created_at': entry.created_at,
                    }
                    for entry in entries
                ],
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'kanban_card_activity error: {e}')
        return json.dumps({'error': str(e)})
