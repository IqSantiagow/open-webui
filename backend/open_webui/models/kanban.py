import logging
import time
from typing import Optional
from uuid import uuid4

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Column, Index, Text, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


####################
# Kanban DB Schema
####################


class KanbanBoard(Base):
    __tablename__ = 'kanban_board'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    folder_id = Column(Text, nullable=True)
    name = Column(Text, nullable=False)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('ix_kanban_board_user_id', 'user_id'),
        Index('ix_kanban_board_user_folder', 'user_id', 'folder_id'),
    )


class KanbanColumn(Base):
    __tablename__ = 'kanban_column'

    id = Column(Text, primary_key=True)
    board_id = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    order = Column(BigInteger, nullable=False, default=0)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (Index('ix_kanban_column_board_order', 'board_id', 'order'),)


class KanbanCard(Base):
    __tablename__ = 'kanban_card'

    id = Column(Text, primary_key=True)
    board_id = Column(Text, nullable=False)
    column_id = Column(Text, nullable=False)

    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)  # markdown
    order = Column(BigInteger, nullable=False, default=0)

    owner = Column(Text, nullable=True)  # user id albo nazwa agenta
    assigned_agent = Column(Text, nullable=True)
    priority = Column(Text, nullable=True)  # low | medium | high
    tags = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index('ix_kanban_card_column_order', 'column_id', 'order'),
        Index('ix_kanban_card_board_id', 'board_id'),
    )


class KanbanActivity(Base):
    __tablename__ = 'kanban_activity'

    id = Column(Text, primary_key=True)
    card_id = Column(Text, nullable=False)
    actor = Column(Text, nullable=False)  # nazwa uzytkownika albo agenta
    action = Column(Text, nullable=False)  # created | updated | moved | commented | deleted
    payload = Column(JSON, nullable=True)

    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (Index('ix_kanban_activity_card_created', 'card_id', 'created_at'),)


####################
# Pydantic Models
####################

PRIORITIES = ('low', 'medium', 'high')


class KanbanBoardModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    folder_id: Optional[str] = None
    name: str
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class KanbanColumnModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    board_id: str
    name: str
    order: int

    created_at: int
    updated_at: int


class KanbanCardModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    board_id: str
    column_id: str

    title: str
    description: Optional[str] = None
    order: int

    owner: Optional[str] = None
    assigned_agent: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[list[str]] = None
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class KanbanActivityModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    card_id: str
    actor: str
    action: str
    payload: Optional[dict] = None

    created_at: int


####################
# Forms
####################


class KanbanBoardForm(BaseModel):
    name: str
    folder_id: Optional[str] = None
    meta: Optional[dict] = None


class KanbanBoardUpdateForm(BaseModel):
    name: Optional[str] = None
    folder_id: Optional[str] = None
    meta: Optional[dict] = None


class KanbanColumnForm(BaseModel):
    name: str


class KanbanColumnUpdateForm(BaseModel):
    name: Optional[str] = None


class KanbanColumnReorderForm(BaseModel):
    column_ids: list[str]


class KanbanCardForm(BaseModel):
    column_id: str
    title: str
    description: Optional[str] = None
    owner: Optional[str] = None
    assigned_agent: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[list[str]] = None
    meta: Optional[dict] = None


class KanbanCardUpdateForm(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    assigned_agent: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[list[str]] = None
    meta: Optional[dict] = None


class KanbanCardMoveForm(BaseModel):
    column_id: str
    position: Optional[int] = None


class KanbanCommentForm(BaseModel):
    text: str


####################
# Responses
####################


class KanbanColumnResponse(KanbanColumnModel):
    cards: list[KanbanCardModel] = []


class KanbanBoardResponse(BaseModel):
    board: KanbanBoardModel
    columns: list[KanbanColumnResponse] = []


class KanbanBoardItemResponse(KanbanBoardModel):
    card_count: int = 0


####################
# KanbanTable
####################

DEFAULT_BOARD_NAME = 'Kanban'
DEFAULT_COLUMN_NAMES = ('Backlog', 'In Progress', 'Review', 'Done')


class KanbanTable:
    ####################
    # Boards
    ####################

    async def get_or_create_default_board(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> KanbanBoardModel:
        """
        Zwraca najstarsza tablice uzytkownika. Jesli uzytkownik nie ma jeszcze zadnej
        tablicy, tworzy ja razem z domyslnym zestawem kolumn.
        """
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(KanbanBoard).filter_by(user_id=user_id).order_by(KanbanBoard.created_at.asc()).limit(1)
            )
            board = result.scalars().first()
            if board:
                return KanbanBoardModel.model_validate(board)

            return await self.insert_board(user_id, KanbanBoardForm(name=DEFAULT_BOARD_NAME), db=db)

    async def insert_board(
        self, user_id: str, form: KanbanBoardForm, db: Optional[AsyncSession] = None
    ) -> KanbanBoardModel:
        """
        Tworzy nowa tablice razem z domyslnym zestawem kolumn, zeby uzytkownik
        nie musial budowac jej od zera.
        """
        async with get_async_db_context(db) as db:
            now = int(time.time_ns())
            board = KanbanBoard(
                id=str(uuid4()),
                user_id=user_id,
                folder_id=form.folder_id,
                name=form.name,
                meta=form.meta,
                created_at=now,
                updated_at=now,
            )
            db.add(board)

            for index, column_name in enumerate(DEFAULT_COLUMN_NAMES):
                db.add(
                    KanbanColumn(
                        id=str(uuid4()),
                        board_id=board.id,
                        name=column_name,
                        order=index,
                        created_at=now,
                        updated_at=now,
                    )
                )

            await db.commit()
            return KanbanBoardModel.model_validate(board)

    async def get_boards_by_user_id(
        self, user_id: str, db: Optional[AsyncSession] = None
    ) -> list[KanbanBoardItemResponse]:
        """
        Lista tablic uzytkownika razem z liczba kart, uzywana przez selektor tablic.
        """
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(KanbanBoard).filter_by(user_id=user_id).order_by(KanbanBoard.created_at.asc())
            )
            boards = result.scalars().all()

            count_result = await db.execute(
                select(KanbanCard.board_id, func.count(KanbanCard.id)).group_by(KanbanCard.board_id)
            )
            card_counts = dict(count_result.all())

            return [
                KanbanBoardItemResponse(
                    **KanbanBoardModel.model_validate(board).model_dump(),
                    card_count=card_counts.get(board.id, 0),
                )
                for board in boards
            ]

    async def update_board_by_id(
        self, id: str, form: KanbanBoardUpdateForm, db: Optional[AsyncSession] = None
    ) -> Optional[KanbanBoardModel]:
        async with get_async_db_context(db) as db:
            board = await db.get(KanbanBoard, id)
            if not board:
                return None

            data = form.model_dump(exclude_unset=True)
            if 'name' in data and data['name'] is not None:
                board.name = data['name']
            if 'folder_id' in data:
                board.folder_id = data['folder_id'] or None
            if 'meta' in data:
                board.meta = {**(board.meta or {}), **(data['meta'] or {})}

            board.updated_at = int(time.time_ns())
            await db.commit()
            return KanbanBoardModel.model_validate(board)

    async def delete_board_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        """
        Usuwa tablice razem z kolumnami, kartami i ich aktywnoscia.
        """
        try:
            async with get_async_db_context(db) as db:
                card_result = await db.execute(select(KanbanCard.id).filter_by(board_id=id))
                card_ids = list(card_result.scalars().all())

                if card_ids:
                    await db.execute(delete(KanbanActivity).filter(KanbanActivity.card_id.in_(card_ids)))

                await db.execute(delete(KanbanCard).filter(KanbanCard.board_id == id))
                await db.execute(delete(KanbanColumn).filter(KanbanColumn.board_id == id))
                await db.execute(delete(KanbanBoard).filter(KanbanBoard.id == id))
                await db.commit()
                return True
        except Exception as e:
            log.exception(f'delete_board_by_id error: {e}')
            return False

    async def clear_folder_ids(
        self, user_id: str, folder_ids: list[str], db: Optional[AsyncSession] = None
    ) -> int:
        """
        Odpina tablice od usunietych folderow, zeby nie zostawaly osierocone wpisy.
        """
        if not folder_ids:
            return 0

        async with get_async_db_context(db) as db:
            result = await db.execute(
                update(KanbanBoard)
                .where(KanbanBoard.user_id == user_id, KanbanBoard.folder_id.in_(folder_ids))
                .values(folder_id=None, updated_at=int(time.time_ns()))
            )
            await db.commit()
            return result.rowcount or 0

    async def get_board_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[KanbanBoardModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(KanbanBoard, id)
            return KanbanBoardModel.model_validate(row) if row else None

    async def get_board_with_cards(
        self, board_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[KanbanBoardResponse]:
        async with get_async_db_context(db) as db:
            board = await db.get(KanbanBoard, board_id)
            if not board:
                return None

            column_result = await db.execute(
                select(KanbanColumn).filter_by(board_id=board_id).order_by(KanbanColumn.order.asc())
            )
            columns = column_result.scalars().all()

            card_result = await db.execute(
                select(KanbanCard).filter_by(board_id=board_id).order_by(KanbanCard.order.asc())
            )
            cards = card_result.scalars().all()

            cards_by_column: dict[str, list[KanbanCardModel]] = {}
            for card in cards:
                cards_by_column.setdefault(card.column_id, []).append(KanbanCardModel.model_validate(card))

            return KanbanBoardResponse(
                board=KanbanBoardModel.model_validate(board),
                columns=[
                    KanbanColumnResponse(
                        **KanbanColumnModel.model_validate(column).model_dump(),
                        cards=cards_by_column.get(column.id, []),
                    )
                    for column in columns
                ],
            )

    ####################
    # Columns
    ####################

    async def get_column_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[KanbanColumnModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(KanbanColumn, id)
            return KanbanColumnModel.model_validate(row) if row else None

    async def get_columns_by_board_id(
        self, board_id: str, db: Optional[AsyncSession] = None
    ) -> list[KanbanColumnModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(
                select(KanbanColumn).filter_by(board_id=board_id).order_by(KanbanColumn.order.asc())
            )
            return [KanbanColumnModel.model_validate(row) for row in result.scalars().all()]

    async def insert_column(
        self, board_id: str, form: KanbanColumnForm, db: Optional[AsyncSession] = None
    ) -> KanbanColumnModel:
        async with get_async_db_context(db) as db:
            now = int(time.time_ns())
            max_order_result = await db.execute(
                select(func.max(KanbanColumn.order)).filter_by(board_id=board_id)
            )
            max_order = max_order_result.scalar()

            row = KanbanColumn(
                id=str(uuid4()),
                board_id=board_id,
                name=form.name,
                order=0 if max_order is None else max_order + 1,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.commit()
            return KanbanColumnModel.model_validate(row)

    async def update_column_by_id(
        self, id: str, form: KanbanColumnUpdateForm, db: Optional[AsyncSession] = None
    ) -> Optional[KanbanColumnModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(KanbanColumn, id)
            if not row:
                return None

            data = form.model_dump(exclude_unset=True)
            if 'name' in data and data['name'] is not None:
                row.name = data['name']

            row.updated_at = int(time.time_ns())
            await db.commit()
            return KanbanColumnModel.model_validate(row)

    async def delete_column_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        """
        Usuwa kolumne razem z jej kartami i aktywnoscia tych kart.
        """
        try:
            async with get_async_db_context(db) as db:
                card_result = await db.execute(select(KanbanCard.id).filter_by(column_id=id))
                card_ids = list(card_result.scalars().all())

                if card_ids:
                    await db.execute(delete(KanbanActivity).filter(KanbanActivity.card_id.in_(card_ids)))
                    await db.execute(delete(KanbanCard).filter(KanbanCard.column_id == id))

                await db.execute(delete(KanbanColumn).filter(KanbanColumn.id == id))
                await db.commit()
                return True
        except Exception as e:
            log.exception(f'delete_column_by_id error: {e}')
            return False

    async def reorder_columns(
        self, board_id: str, column_ids: list[str], db: Optional[AsyncSession] = None
    ) -> list[KanbanColumnModel]:
        async with get_async_db_context(db) as db:
            now = int(time.time_ns())
            result = await db.execute(select(KanbanColumn).filter_by(board_id=board_id))
            columns = {row.id: row for row in result.scalars().all()}

            for index, column_id in enumerate(column_ids):
                row = columns.get(column_id)
                if row:
                    row.order = index
                    row.updated_at = now

            await db.commit()
            return await self.get_columns_by_board_id(board_id, db=db)

    ####################
    # Cards
    ####################

    async def get_card_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[KanbanCardModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(KanbanCard, id)
            return KanbanCardModel.model_validate(row) if row else None

    async def search_cards(
        self,
        board_id: str,
        query: Optional[str] = None,
        column_id: Optional[str] = None,
        owner: Optional[str] = None,
        tag: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> list[KanbanCardModel]:
        async with get_async_db_context(db) as db:
            stmt = select(KanbanCard).filter_by(board_id=board_id)

            if column_id:
                stmt = stmt.filter(KanbanCard.column_id == column_id)
            if owner:
                stmt = stmt.filter(or_(KanbanCard.owner == owner, KanbanCard.assigned_agent == owner))
            if query:
                search = f'%{query}%'
                stmt = stmt.filter(or_(KanbanCard.title.ilike(search), KanbanCard.description.ilike(search)))

            stmt = stmt.order_by(KanbanCard.order.asc())

            if skip:
                stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)

            result = await db.execute(stmt)
            cards = [KanbanCardModel.model_validate(row) for row in result.scalars().all()]

            # Tagi trzymamy w JSON, wiec filtrujemy je po stronie aplikacji.
            if tag:
                cards = [card for card in cards if tag in (card.tags or [])]

            return cards

    async def insert_card(
        self, board_id: str, form: KanbanCardForm, db: Optional[AsyncSession] = None
    ) -> KanbanCardModel:
        async with get_async_db_context(db) as db:
            now = int(time.time_ns())
            max_order_result = await db.execute(
                select(func.max(KanbanCard.order)).filter_by(column_id=form.column_id)
            )
            max_order = max_order_result.scalar()

            row = KanbanCard(
                id=str(uuid4()),
                board_id=board_id,
                column_id=form.column_id,
                title=form.title,
                description=form.description,
                order=0 if max_order is None else max_order + 1,
                owner=form.owner,
                assigned_agent=form.assigned_agent,
                priority=form.priority,
                tags=form.tags,
                meta=form.meta,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.commit()
            return KanbanCardModel.model_validate(row)

    async def update_card_by_id(
        self, id: str, form: KanbanCardUpdateForm, db: Optional[AsyncSession] = None
    ) -> Optional[KanbanCardModel]:
        async with get_async_db_context(db) as db:
            row = await db.get(KanbanCard, id)
            if not row:
                return None

            data = form.model_dump(exclude_unset=True)
            for field in ('title', 'description', 'owner', 'assigned_agent', 'priority', 'tags'):
                if field in data:
                    setattr(row, field, data[field])

            if 'meta' in data:
                row.meta = {**(row.meta or {}), **(data['meta'] or {})}

            row.updated_at = int(time.time_ns())
            await db.commit()
            return KanbanCardModel.model_validate(row)

    async def move_card_by_id(
        self,
        id: str,
        column_id: str,
        position: Optional[int] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[KanbanCardModel]:
        """
        Przenosi karte do wskazanej kolumny na wskazana pozycje i przelicza
        kolejnosc kart w kolumnie zrodlowej oraz docelowej.
        """
        async with get_async_db_context(db) as db:
            row = await db.get(KanbanCard, id)
            if not row:
                return None

            now = int(time.time_ns())
            source_column_id = row.column_id

            target_result = await db.execute(
                select(KanbanCard)
                .filter(KanbanCard.column_id == column_id, KanbanCard.id != id)
                .order_by(KanbanCard.order.asc())
            )
            target_cards = list(target_result.scalars().all())

            insert_at = len(target_cards) if position is None else max(0, min(position, len(target_cards)))
            target_cards.insert(insert_at, row)

            row.column_id = column_id
            row.updated_at = now

            for index, card in enumerate(target_cards):
                card.order = index
                card.updated_at = now

            if source_column_id != column_id:
                source_result = await db.execute(
                    select(KanbanCard)
                    .filter(KanbanCard.column_id == source_column_id)
                    .order_by(KanbanCard.order.asc())
                )
                for index, card in enumerate(source_result.scalars().all()):
                    card.order = index
                    card.updated_at = now

            await db.commit()
            return KanbanCardModel.model_validate(row)

    async def delete_card_by_id(self, id: str, db: Optional[AsyncSession] = None) -> bool:
        try:
            async with get_async_db_context(db) as db:
                await db.execute(delete(KanbanActivity).filter(KanbanActivity.card_id == id))
                await db.execute(delete(KanbanCard).filter(KanbanCard.id == id))
                await db.commit()
                return True
        except Exception as e:
            log.exception(f'delete_card_by_id error: {e}')
            return False

    ####################
    # Activity
    ####################

    async def insert_activity(
        self,
        card_id: str,
        actor: str,
        action: str,
        payload: Optional[dict] = None,
        db: Optional[AsyncSession] = None,
    ) -> KanbanActivityModel:
        async with get_async_db_context(db) as db:
            row = KanbanActivity(
                id=str(uuid4()),
                card_id=card_id,
                actor=actor,
                action=action,
                payload=payload,
                created_at=int(time.time_ns()),
            )
            db.add(row)
            await db.commit()
            return KanbanActivityModel.model_validate(row)

    async def get_activity_by_card_id(
        self, card_id: str, limit: int = 50, db: Optional[AsyncSession] = None
    ) -> list[KanbanActivityModel]:
        async with get_async_db_context(db) as db:
            stmt = (
                select(KanbanActivity)
                .filter_by(card_id=card_id)
                .order_by(KanbanActivity.created_at.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            return [KanbanActivityModel.model_validate(row) for row in result.scalars().all()]


Kanban = KanbanTable()
