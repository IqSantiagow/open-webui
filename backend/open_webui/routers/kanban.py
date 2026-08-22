import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_async_session
from open_webui.models.folders import Folders
from open_webui.models.kanban import (
    PRIORITIES,
    Kanban,
    KanbanActivityModel,
    KanbanBoardForm,
    KanbanBoardItemResponse,
    KanbanBoardModel,
    KanbanBoardResponse,
    KanbanBoardUpdateForm,
    KanbanCardForm,
    KanbanCardModel,
    KanbanCardMoveForm,
    KanbanCardUpdateForm,
    KanbanColumnForm,
    KanbanColumnModel,
    KanbanColumnReorderForm,
    KanbanColumnUpdateForm,
    KanbanCommentForm,
)
from open_webui.socket.main import emit_to_users
from open_webui.utils.auth import get_verified_user
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Helpers
############################


async def get_user_board(user, db: AsyncSession, board_id: Optional[str] = None):
    """
    Zwraca wskazana tablice uzytkownika, a bez podanego identyfikatora - tablice
    domyslna (tworzona przy pierwszym uzyciu).
    """
    if not board_id:
        return await Kanban.get_or_create_default_board(user.id, db=db)

    return await check_board_access(board_id, user, db=db)


async def check_board_access(board_id: str, user, db: AsyncSession) -> KanbanBoardModel:
    board = await Kanban.get_board_by_id(board_id, db=db)
    if not board or board.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    return board


async def check_folder_access(folder_id: Optional[str], user, db: AsyncSession) -> None:
    if not folder_id:
        return

    folder = await Folders.get_folder_by_id_and_user_id(folder_id, user.id, db=db)
    if not folder:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)


async def check_column_access(column_id: str, user, db: AsyncSession) -> KanbanColumnModel:
    column = await Kanban.get_column_by_id(column_id, db=db)
    if not column:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    board = await Kanban.get_board_by_id(column.board_id, db=db)
    if not board or board.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    return column


async def check_card_access(card_id: str, user, db: AsyncSession) -> KanbanCardModel:
    card = await Kanban.get_card_by_id(card_id, db=db)
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    board = await Kanban.get_board_by_id(card.board_id, db=db)
    if not board or board.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    return card


def validate_priority(priority: Optional[str]) -> None:
    if priority is not None and priority not in PRIORITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(f'Priority must be one of: {", ".join(PRIORITIES)}'),
        )


async def notify_board_change(user_id: str, action: str, payload: dict) -> None:
    """
    Informuje otwarte tablice uzytkownika o zmianie, zeby zmiany wprowadzone przez
    agentow pojawialy sie bez odswiezania strony.
    """
    await emit_to_users('events:kanban', {'action': action, **payload}, [user_id])


############################
# Boards
############################


@router.get('/boards', response_model=list[KanbanBoardItemResponse])
async def get_boards(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    boards = await Kanban.get_boards_by_user_id(user.id, db=db)
    if not boards:
        await Kanban.get_or_create_default_board(user.id, db=db)
        boards = await Kanban.get_boards_by_user_id(user.id, db=db)

    return boards


@router.post('/boards', response_model=Optional[KanbanBoardModel])
async def create_board(
    form_data: KanbanBoardForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_folder_access(form_data.folder_id, user, db=db)

    try:
        board = await Kanban.insert_board(user.id, form_data, db=db)
        await notify_board_change(user.id, 'board.created', {'board_id': board.id})
        return board
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.post('/boards/{id}/update', response_model=Optional[KanbanBoardModel])
async def update_board_by_id(
    id: str,
    form_data: KanbanBoardUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_board_access(id, user, db=db)
    await check_folder_access(form_data.folder_id, user, db=db)

    try:
        board = await Kanban.update_board_by_id(id, form_data, db=db)
        await notify_board_change(user.id, 'board.updated', {'board_id': id})
        return board
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.delete('/boards/{id}', response_model=bool)
async def delete_board_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_board_access(id, user, db=db)

    result = await Kanban.delete_board_by_id(id, db=db)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    await notify_board_change(user.id, 'board.deleted', {'board_id': id})
    return result


@router.get('/board', response_model=Optional[KanbanBoardResponse])
async def get_board(
    board_id: Optional[str] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    board = await get_user_board(user, db=db, board_id=board_id)
    return await Kanban.get_board_with_cards(board.id, db=db)


############################
# Columns
############################


@router.post('/columns', response_model=Optional[KanbanColumnModel])
async def create_column(
    form_data: KanbanColumnForm,
    board_id: Optional[str] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    board = await get_user_board(user, db=db, board_id=board_id)

    try:
        column = await Kanban.insert_column(board.id, form_data, db=db)
        await notify_board_change(user.id, 'column.created', {'column_id': column.id})
        return column
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.post('/columns/reorder', response_model=list[KanbanColumnModel])
async def reorder_columns(
    form_data: KanbanColumnReorderForm,
    board_id: Optional[str] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    board = await get_user_board(user, db=db, board_id=board_id)

    try:
        columns = await Kanban.reorder_columns(board.id, form_data.column_ids, db=db)
        await notify_board_change(user.id, 'column.reordered', {'board_id': board.id})
        return columns
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.post('/columns/{id}/update', response_model=Optional[KanbanColumnModel])
async def update_column_by_id(
    id: str,
    form_data: KanbanColumnUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_column_access(id, user, db=db)

    try:
        column = await Kanban.update_column_by_id(id, form_data, db=db)
        await notify_board_change(user.id, 'column.updated', {'column_id': id})
        return column
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.delete('/columns/{id}', response_model=bool)
async def delete_column_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_column_access(id, user, db=db)

    result = await Kanban.delete_column_by_id(id, db=db)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    await notify_board_change(user.id, 'column.deleted', {'column_id': id})
    return result


############################
# Cards
############################


@router.post('/cards', response_model=Optional[KanbanCardModel])
async def create_card(
    form_data: KanbanCardForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    column = await check_column_access(form_data.column_id, user, db=db)
    validate_priority(form_data.priority)

    try:
        card = await Kanban.insert_card(column.board_id, form_data, db=db)
        await Kanban.insert_activity(card.id, user.name, 'created', {'title': card.title}, db=db)
        await notify_board_change(user.id, 'card.created', {'card_id': card.id})
        return card
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.post('/cards/{id}/update', response_model=Optional[KanbanCardModel])
async def update_card_by_id(
    id: str,
    form_data: KanbanCardUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_card_access(id, user, db=db)
    validate_priority(form_data.priority)

    try:
        card = await Kanban.update_card_by_id(id, form_data, db=db)
        await Kanban.insert_activity(
            id,
            user.name,
            'updated',
            {'fields': list(form_data.model_dump(exclude_unset=True).keys())},
            db=db,
        )
        await notify_board_change(user.id, 'card.updated', {'card_id': id})
        return card
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.post('/cards/{id}/move', response_model=Optional[KanbanCardModel])
async def move_card_by_id(
    id: str,
    form_data: KanbanCardMoveForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    card = await check_card_access(id, user, db=db)
    target_column = await check_column_access(form_data.column_id, user, db=db)

    if target_column.board_id != card.board_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    try:
        moved_card = await Kanban.move_card_by_id(id, form_data.column_id, form_data.position, db=db)
        if card.column_id != form_data.column_id:
            await Kanban.insert_activity(
                id,
                user.name,
                'moved',
                {'to_column': target_column.name},
                db=db,
            )
        await notify_board_change(user.id, 'card.moved', {'card_id': id})
        return moved_card
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())


@router.delete('/cards/{id}', response_model=bool)
async def delete_card_by_id(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_card_access(id, user, db=db)

    result = await Kanban.delete_card_by_id(id, db=db)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())

    await notify_board_change(user.id, 'card.deleted', {'card_id': id})
    return result


############################
# Activity
############################


@router.get('/cards/{id}/activity', response_model=list[KanbanActivityModel])
async def get_card_activity(
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_card_access(id, user, db=db)
    return await Kanban.get_activity_by_card_id(id, db=db)


@router.post('/cards/{id}/comment', response_model=Optional[KanbanActivityModel])
async def create_card_comment(
    id: str,
    form_data: KanbanCommentForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_card_access(id, user, db=db)

    try:
        activity = await Kanban.insert_activity(id, user.name, 'commented', {'text': form_data.text}, db=db)
        await notify_board_change(user.id, 'card.commented', {'card_id': id})
        return activity
    except Exception as e:
        log.exception(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT())
