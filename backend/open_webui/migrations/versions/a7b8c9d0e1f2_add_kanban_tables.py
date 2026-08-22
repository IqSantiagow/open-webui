"""add kanban tables

Revision ID: a7b8c9d0e1f2
Revises: f0bd01a18a3d
Create Date: 2026-08-22
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f0bd01a18a3d'
branch_labels = None
depends_on = None


def _index_exists(inspector, index_name, table_name):
    """Check if an index already exists on the given table (works for both SQLite and PostgreSQL)."""
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def _create_index_if_missing(inspector, index_name, table_name, columns):
    inspector.clear_cache()
    if table_name in inspector.get_table_names() and not _index_exists(inspector, index_name, table_name):
        op.create_index(index_name, table_name, columns)


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'kanban_board' not in tables:
        op.create_table(
            'kanban_board',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    _create_index_if_missing(inspector, 'ix_kanban_board_user_id', 'kanban_board', ['user_id'])

    if 'kanban_column' not in tables:
        op.create_table(
            'kanban_column',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('board_id', sa.Text(), nullable=False),
            sa.Column('name', sa.Text(), nullable=False),
            sa.Column('order', sa.BigInteger(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    _create_index_if_missing(inspector, 'ix_kanban_column_board_order', 'kanban_column', ['board_id', 'order'])

    if 'kanban_card' not in tables:
        op.create_table(
            'kanban_card',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('board_id', sa.Text(), nullable=False),
            sa.Column('column_id', sa.Text(), nullable=False),
            sa.Column('title', sa.Text(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('order', sa.BigInteger(), nullable=False),
            sa.Column('owner', sa.Text(), nullable=True),
            sa.Column('assigned_agent', sa.Text(), nullable=True),
            sa.Column('priority', sa.Text(), nullable=True),
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    _create_index_if_missing(inspector, 'ix_kanban_card_column_order', 'kanban_card', ['column_id', 'order'])
    _create_index_if_missing(inspector, 'ix_kanban_card_board_id', 'kanban_card', ['board_id'])

    if 'kanban_activity' not in tables:
        op.create_table(
            'kanban_activity',
            sa.Column('id', sa.Text(), primary_key=True),
            sa.Column('card_id', sa.Text(), nullable=False),
            sa.Column('actor', sa.Text(), nullable=False),
            sa.Column('action', sa.Text(), nullable=False),
            sa.Column('payload', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
        )

    _create_index_if_missing(
        inspector, 'ix_kanban_activity_card_created', 'kanban_activity', ['card_id', 'created_at']
    )


def downgrade():
    op.drop_index('ix_kanban_activity_card_created')
    op.drop_table('kanban_activity')
    op.drop_index('ix_kanban_card_board_id')
    op.drop_index('ix_kanban_card_column_order')
    op.drop_table('kanban_card')
    op.drop_index('ix_kanban_column_board_order')
    op.drop_table('kanban_column')
    op.drop_index('ix_kanban_board_user_id')
    op.drop_table('kanban_board')
