"""scope list setting uniqueness to owner

Revision ID: 56a83e0c9488
Revises: b02a4e9f1c63
Create Date: 2026-10-06 14:11:41.459828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56a83e0c9488'
down_revision: Union[str, Sequence[str], None] = 'b02a4e9f1c63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("server_settings_list", "user_settings_list")


def _rebuild(table_name: str, unique_columns: list[str]) -> None:
    tmp = f"{table_name}_alembic_tmp"

    # A previously failed run can leave this behind; the old table is intact.
    if sa.inspect(op.get_bind()).has_table(tmp):
        op.drop_table(tmp)

    op.create_table(
        tmp,
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uid", sa.VARCHAR()),
        sa.Column("name", sa.VARCHAR()),
        sa.Column("value", sa.VARCHAR()),
        sa.UniqueConstraint(*unique_columns),
    )
    op.execute(
        f"INSERT INTO {tmp} (id, uid, name, value) "
        f"SELECT id, uid, name, value FROM {table_name}"
    )
    op.drop_table(table_name)
    op.rename_table(tmp, table_name)


def _conflicting_rows(table_name: str) -> int:
    row = op.get_bind().execute(
        sa.text(
            f"SELECT COUNT(*) FROM (SELECT 1 FROM {table_name} "
            f"GROUP BY name, value HAVING COUNT(*) > 1)"
        )
    ).scalar()
    return int(row or 0)


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in TABLES:
        _rebuild(table_name, ["uid", "name", "value"])


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in TABLES:
        conflicts = _conflicting_rows(table_name)
        if conflicts:
            raise RuntimeError(
                f"Cannot restore the per-guild unique constraint on {table_name}: "
                f"{conflicts} value(s) are shared across owners. Remove the "
                "duplicates first, or re-run with a schema rebuilt from database.py."
            )
        _rebuild(table_name, ["name", "value"])
