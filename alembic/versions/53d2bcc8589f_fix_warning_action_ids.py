"""fix warning action ids

Revision ID: 53d2bcc8589f
Revises: ea95e4264ab0
Create Date: 2026-11-04 11:26:17.022384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53d2bcc8589f'
down_revision: Union[str, Sequence[str], None] = 'ea95e4264ab0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fetch_rows() -> list[dict]:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT gid, action, warning_count, parameter "
            "FROM moderator_warning_actions ORDER BY id"
        )
    ).mappings().all()

    seen = set()
    unique_rows = []
    for row in rows:
        key = (row["gid"], row["action"], row["warning_count"])
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(dict(row))

    return unique_rows


def upgrade() -> None:
    """Upgrade schema."""
    rows = _fetch_rows()

    op.drop_table("moderator_warning_actions")
    op.create_table(
        "moderator_warning_actions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gid", sa.VARCHAR(), nullable=False),
        sa.Column("action", sa.VARCHAR(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("parameter", sa.VARCHAR(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "gid",
            "action",
            "warning_count",
            name="uq_moderator_warning_actions_gid_action_count",
        ),
    )

    if rows:
        op.bulk_insert(
            sa.table(
                "moderator_warning_actions",
                sa.column("gid", sa.VARCHAR),
                sa.column("action", sa.VARCHAR),
                sa.column("warning_count", sa.Integer),
                sa.column("parameter", sa.VARCHAR),
            ),
            rows,
        )


def downgrade() -> None:
    """Downgrade schema."""
    rows = _fetch_rows()

    op.drop_table("moderator_warning_actions")
    op.create_table(
        "moderator_warning_actions",
        sa.Column("id", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("gid", sa.VARCHAR(), nullable=False),
        sa.Column("action", sa.VARCHAR(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("parameter", sa.VARCHAR(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    if rows:
        op.bulk_insert(
            sa.table(
                "moderator_warning_actions",
                sa.column("id", sa.VARCHAR),
                sa.column("gid", sa.VARCHAR),
                sa.column("action", sa.VARCHAR),
                sa.column("warning_count", sa.Integer),
                sa.column("parameter", sa.VARCHAR),
            ),
            [
                {"id": str(index + 1), **row}
                for index, row in enumerate(rows)
            ],
        )
