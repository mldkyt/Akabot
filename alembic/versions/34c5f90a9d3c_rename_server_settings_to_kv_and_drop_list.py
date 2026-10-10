"""rename server settings to kv, migrate list settings into dedicated tables, drop server_settings_list

Revision ID: 34c5f90a9d3c
Revises: 5a95ec14ae62
Create Date: 2026-10-10 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34c5f90a9d3c'
down_revision: Union[str, Sequence[str], None] = '5a95ec14ae62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _insert(bind, table: str, unique: tuple[str, ...] = (), **values):
    if unique:
        where = " AND ".join(f"{k} = :{k}" for k in unique)
        exists = bind.execute(
            sa.text(f"SELECT 1 FROM {table} WHERE {where}"),
            {k: values[k] for k in unique},
        ).first()
        if exists:
            return
    cols = ", ".join(values)
    marks = ", ".join(":" + k for k in values)
    bind.execute(
        sa.text(f"INSERT INTO {table} ({cols}) VALUES ({marks})"),
        values,
    )


def _migrate_list_to_tables(bind, reverse: bool) -> None:
    if not reverse:
        rows = bind.execute(
            sa.text("SELECT uid, name, value FROM server_settings_list")
        ).fetchall()

        for uid, name, value in rows:
            gid = uid
            if name == "Chat Revive Channels":
                cid, minutes = value.split(";", 1)
                _insert(bind, "chat_revive_channels", ("gid", "cid"), gid=gid, cid=cid, minutes=int(minutes))
            elif name == "Chat summary channels":
                _insert(bind, "chat_summary_channel", ("gid", "cid"), gid=gid, cid=value, messages=0, last_member="0")
            elif name == "Counting channels":
                _insert(bind, "counting", ("gid", "cid"), gid=gid, cid=value, current_count=0, last_counter="0")
            elif name == "Leveling rewards":
                rid, level = value.split(";")
                _insert(bind, "leveling_rewards", ("gid", "rid"), gid=gid, rid=rid, level=int(level))
            elif name == "Leveling Multipliers":
                start, end, multiplier = value.split(";")
                sm, sd = start.split("-")
                em, ed = end.split("-")
                _insert(
                    bind,
                    "leveling_multipliers",
                    gid=gid,
                    start_month=int(sm),
                    start_day=int(sd),
                    end_month=int(em),
                    end_day=int(ed),
                    multiplier=int(multiplier),
                )
            elif name == "Moderator roles":
                _insert(bind, "moderator_roles", ("gid", "rid"), gid=gid, rid=value)
            elif name == "Roles on join":
                _insert(bind, "roles_on_join", ("gid", "rid"), gid=gid, rid=value)
            elif name == "Statistic Channels":
                cid, template = value.split(";", 1)
                _insert(bind, "statistic_channels", ("gid", "cid"), gid=gid, cid=cid, template=template)
            elif name == "Suggestion channels":
                _insert(bind, "suggestion_channels", ("gid", "cid"), gid=gid, cid=value)
            elif name == "Temporary VCs":
                _insert(bind, "temporary_vc_creator_channels", ("gid", "cid"), gid=gid, cid=value)
            elif name == "Automod actions":
                parts = value.split(";")
                action = parts[1]
                if action in ("kick", "ban"):
                    content = ";".join(parts[2:]) if len(parts) > 2 else None
                    _insert(bind, "automod_actions", gid=gid, rule_id=parts[0], action=action, duration=None, content=content)
                elif action == "dm":
                    content = ";".join(parts[2:])
                    _insert(bind, "automod_actions", gid=gid, rule_id=parts[0], action=action, duration=None, content=content)
                elif action == "mute":
                    duration = parts[2]
                    content = ";".join(parts[3:]) if len(parts) > 3 else None
                    _insert(bind, "automod_actions", gid=gid, rule_id=parts[0], action=action, duration=duration, content=content)
    else:
        for table, name, cols, template in [
            ("chat_revive_channels", "Chat Revive Channels", ["gid", "cid", "minutes"], lambda g, c, minutes: f"{c};{minutes}"),
            ("statistic_channels", "Statistic Channels", ["gid", "cid", "template"], lambda g, c, template: f"{c};{template}"),
            ("moderator_roles", "Moderator roles", ["gid", "rid"], lambda g, r: r),
            ("roles_on_join", "Roles on join", ["gid", "rid"], lambda g, r: r),
            ("suggestion_channels", "Suggestion channels", ["gid", "cid"], lambda g, c: c),
            ("temporary_vc_creator_channels", "Temporary VCs", ["gid", "cid"], lambda g, c: c),
        ]:
            for row in bind.execute(sa.text(f"SELECT {', '.join(cols)} FROM {table}")).fetchall():
                _insert(bind, "server_settings_list", ("uid", "name", "value"), uid=row[0], name=name, value=template(*row))
        for gid, cid in bind.execute(sa.text("SELECT gid, cid FROM chat_summary_channel")).fetchall():
            _insert(bind, "server_settings_list", ("uid", "name", "value"), uid=gid, name="Chat summary channels", value=cid)
        for gid, cid in bind.execute(sa.text("SELECT gid, cid FROM counting")).fetchall():
            _insert(bind, "server_settings_list", ("uid", "name", "value"), uid=gid, name="Counting channels", value=cid)
        for gid, rid, level in bind.execute(sa.text("SELECT gid, rid, level FROM leveling_rewards")).fetchall():
            _insert(bind, "server_settings_list", ("uid", "name", "value"), uid=gid, name="Leveling rewards", value=f"{rid};{level}")
        for row in bind.execute(sa.text("SELECT gid, start_month, start_day, end_month, end_day, multiplier FROM leveling_multipliers")).fetchall():
            gid, sm, sd, em, ed, multiplier = row
            value = f"{sm:02}-{sd:02};{em:02}-{ed:02};{multiplier}"
            _insert(bind, "server_settings_list", ("uid", "name", "value"), uid=gid, name="Leveling Multipliers", value=value)
        for gid, rule_id, action, duration, content in bind.execute(sa.text("SELECT gid, rule_id, action, duration, content FROM automod_actions")).fetchall():
            if action in ("kick", "ban"):
                value = f"{rule_id};{action}" + (f";{content}" if content else "")
            elif action == "dm":
                value = f"{rule_id};{action};{content}"
            else:
                value = f"{rule_id};{action};{duration}" + (f";{content}" if content else "")
            _insert(bind, "server_settings_list", ("uid", "name", "value"), uid=gid, name="Automod actions", value=value)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    op.rename_table("server_settings", "kv")
    _migrate_list_to_tables(bind, reverse=False)
    op.drop_table("server_settings_list")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    op.create_table(
        "server_settings_list",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("uid", sa.VARCHAR(), nullable=True),
        sa.Column("name", sa.VARCHAR(), nullable=True),
        sa.Column("value", sa.VARCHAR(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uid", "name", "value"),
    )
    _migrate_list_to_tables(bind, reverse=True)
    op.rename_table("kv", "server_settings")