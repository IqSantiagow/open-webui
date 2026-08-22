"""add kanban board folder id

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-08-22
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def _column_exists(inspector, table_name, column_name):
    return any(column['name'] == column_name for column in inspector.get_columns(table_name))


def _index_exists(inspector, index_name, table_name):
    return any(idx['name'] == index_name for idx in inspector.get_indexes(table_name))


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if 'kanban_board' not in inspector.get_table_names():
        return

    if not _column_exists(inspector, 'kanban_board', 'folder_id'):
        op.add_column('kanban_board', sa.Column('folder_id', sa.Text(), nullable=True))

    inspector.clear_cache()
    if not _index_exists(inspector, 'ix_kanban_board_user_folder', 'kanban_board'):
        op.create_index('ix_kanban_board_user_folder', 'kanban_board', ['user_id', 'folder_id'])


def downgrade():
    op.drop_index('ix_kanban_board_user_folder')
    op.drop_column('kanban_board', 'folder_id')
