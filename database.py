import json
import os.path

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, VARCHAR, UniqueConstraint, DATE, \
    StaticPool

if not os.path.exists("data"):
    os.mkdir("data")

engine = create_engine(
    os.getenv("DB_URL", "sqlite:///data/nekona.db"),
    connect_args=json.loads(os.getenv("DB_ARGS") or "{}"),
    poolclass=StaticPool
)

md_obj = MetaData()

# Declare tables

server_settings = Table(
    "server_settings",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("name", VARCHAR, primary_key=True),
    Column("value", VARCHAR)
)

user_settings = Table(
    "user_settings",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("name", VARCHAR, primary_key=True),
    Column("value", VARCHAR)
)

server_settings_list = Table(
    "server_settings_list",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("uid", VARCHAR),
    Column("name", VARCHAR),
    Column("value", VARCHAR),
    UniqueConstraint("name", "value")
)

user_settings_list = Table(
    "user_settings_list",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("uid", VARCHAR),
    Column("name", VARCHAR),
    Column("value", VARCHAR),
    UniqueConstraint("name", "value")
)

leveling = Table(
    "leveling",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("gid", VARCHAR, primary_key=True),
    Column("xp", Integer)
)

# Chat Summary

chat_summary_channels = Table(
    "chat_summary_channel",
    md_obj,
    Column("gid", VARCHAR, primary_key=True, comment="Guild ID"),
    Column("cid", VARCHAR, primary_key=True, comment="Channel ID"),
    Column("messages", Integer),
    Column("last_member", VARCHAR, default="0", nullable=False)
)

chat_summary_members = Table(
    "chat_summary_members",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("messages", Integer)
)

monthly_chat_summary_channels = Table(
    "chat_summary_channel_monthly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True, comment="Guild ID"),
    Column("cid", VARCHAR, primary_key=True, comment="Channel ID"),
    Column("messages", Integer),
    Column("last_member", VARCHAR, default="0", nullable=False)
)

monthly_chat_summary_members = Table(
    "chat_summary_members_monthly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("messages", Integer)
)

yearly_chat_summary_channels = Table(
    "chat_summary_channel_yearly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True, comment="Guild ID"),
    Column("cid", VARCHAR, primary_key=True, comment="Channel ID"),
    Column("messages", Integer),
    Column("last_member", VARCHAR, default="0", nullable=False)
)

yearly_chat_summary_members = Table(
    "chat_summary_members_yearly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("messages", Integer)
)

chat_streaks = Table(
    "chat_streaks",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("start_date", DATE, nullable=False, comment="YYYY-MM-DD"),
    Column("last_message_date", DATE, nullable=False, comment="YYYY-MM-DD")
)

counting_channels = Table(
    "counting",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("current_count", Integer, nullable=False),
    Column("last_counter", VARCHAR, nullable=False, default="0")
)
