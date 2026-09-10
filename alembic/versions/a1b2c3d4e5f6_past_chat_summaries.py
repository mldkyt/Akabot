"""past chat summaries

Revision ID: a1b2c3d4e5f6
Revises: ba3dd45fa976
Create Date: 2026-09-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ba3dd45fa976'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('past_chat_summaries',
    sa.Column('id', sa.VARCHAR(), nullable=False),
    sa.Column('gid', sa.VARCHAR(), nullable=False),
    sa.Column('cid', sa.VARCHAR(), nullable=False),
    sa.Column('kind', sa.VARCHAR(), nullable=False),
    sa.Column('period', sa.VARCHAR(), nullable=False),
    sa.Column('total_messages', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_past_chat_summaries_gid_cid_kind_period', 'past_chat_summaries', ['gid', 'cid', 'kind', 'period'])

    op.create_table('past_chat_summaries_rows',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('summary_id', sa.VARCHAR(), nullable=False),
    sa.Column('uid', sa.VARCHAR(), nullable=False),
    sa.Column('messages', sa.Integer(), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['summary_id'], ['past_chat_summaries.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_past_chat_summaries_rows_summary_id', 'past_chat_summaries_rows', ['summary_id'])


def downgrade() -> None:
    op.drop_index('ix_past_chat_summaries_rows_summary_id')
    op.drop_table('past_chat_summaries_rows')
    op.drop_index('ix_past_chat_summaries_gid_cid_kind_period')
    op.drop_table('past_chat_summaries')
