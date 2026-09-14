"""premium unlimited codes

Revision ID: b02a4e9f1c63
Revises: a1f2c3d4e5f6
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b02a4e9f1c63'
down_revision: Union[str, Sequence[str], None] = 'a1f2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('premium_tokens') as batch_op:
        batch_op.add_column(
            sa.Column('unlimited', sa.Boolean(), nullable=False, server_default=sa.text('0'))
        )
    with op.batch_alter_table('premium_guilds') as batch_op:
        batch_op.add_column(
            sa.Column('unlimited', sa.Boolean(), nullable=False, server_default=sa.text('0'))
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('premium_guilds') as batch_op:
        batch_op.drop_column('unlimited')
    with op.batch_alter_table('premium_tokens') as batch_op:
        batch_op.drop_column('unlimited')