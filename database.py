import json
import os.path

from sqlalchemy import (
    DATE,
    VARCHAR,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    StaticPool,
    Table,
    UniqueConstraint,
    create_engine,
)

if not os.path.exists("data"):
    os.mkdir("data")

engine = create_engine(
    os.getenv("DB_URL", "sqlite:///data/akabot.db"),
    connect_args=json.loads(os.getenv("DB_ARGS") or "{}"),
    poolclass=StaticPool,
)

md_obj = MetaData()

# Declare tables

server_settings = Table(
    "server_settings",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("name", VARCHAR, primary_key=True),
    Column("value", VARCHAR),
)

user_settings = Table(
    "user_settings",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("name", VARCHAR, primary_key=True),
    Column("value", VARCHAR),
)

server_settings_list = Table(
    "server_settings_list",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("uid", VARCHAR),
    Column("name", VARCHAR),
    Column("value", VARCHAR),
    UniqueConstraint("name", "value"),
)

user_settings_list = Table(
    "user_settings_list",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("uid", VARCHAR),
    Column("name", VARCHAR),
    Column("value", VARCHAR),
    UniqueConstraint("name", "value"),
)

leveling = Table(
    "leveling",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("gid", VARCHAR, primary_key=True),
    Column("xp", Integer),
)

# Chat Summary

chat_summary_channels = Table(
    "chat_summary_channel",
    md_obj,
    Column("gid", VARCHAR, primary_key=True, comment="Guild ID"),
    Column("cid", VARCHAR, primary_key=True, comment="Channel ID"),
    Column("messages", Integer),
    Column("last_member", VARCHAR, default="0", nullable=False),
)

chat_summary_members = Table(
    "chat_summary_members",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("messages", Integer),
)

monthly_chat_summary_channels = Table(
    "chat_summary_channel_monthly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True, comment="Guild ID"),
    Column("cid", VARCHAR, primary_key=True, comment="Channel ID"),
    Column("messages", Integer),
    Column("last_member", VARCHAR, default="0", nullable=False),
)

monthly_chat_summary_members = Table(
    "chat_summary_members_monthly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("messages", Integer),
)

yearly_chat_summary_channels = Table(
    "chat_summary_channel_yearly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True, comment="Guild ID"),
    Column("cid", VARCHAR, primary_key=True, comment="Channel ID"),
    Column("messages", Integer),
    Column("last_member", VARCHAR, default="0", nullable=False),
)

yearly_chat_summary_members = Table(
    "chat_summary_members_yearly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("messages", Integer),
)

chat_streaks = Table(
    "chat_streaks",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("start_date", DATE, nullable=False, comment="YYYY-MM-DD"),
    Column("last_message_date", DATE, nullable=False, comment="YYYY-MM-DD"),
)

counting_channels = Table(
    "counting",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("current_count", Integer, nullable=False),
    Column("last_counter", VARCHAR, nullable=False, default="0"),
)

economy_money = Table(
    "economy_money",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),  # user id
    Column("wallet", Integer, nullable=False, default=0),  # player money in wallet
    Column("bank", Integer, nullable=False, default=1000),  # player money in bank
)

economy_work = Table(
    "economy_work",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("expires_at", DateTime),  # the expiry date, null if not any
)

chat_revive = Table(
    "chat_revive",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("notif_time", DateTime, nullable=False),
)

temporary_vcs = Table(
    "temporary_vcs",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
)

vc_notifications_all = Table(
    "vc_notifs_all",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("gid", VARCHAR, primary_key=True),
)

vc_notifications_user = Table(
    "vc_notifs_user",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("gid", VARCHAR, primary_key=True),
    Column("tid", VARCHAR, primary_key=True),
)

vc_notifications_channel = Table(
    "vc_notifs_channel",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("gid", VARCHAR, primary_key=True),
    Column("tid", VARCHAR, primary_key=True),
)

mail = Table(
    "mail",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("text", VARCHAR, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("author", VARCHAR, nullable=False),
)

mail_read = Table(
    "mail_read",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("mail_id", Integer, ForeignKey("mail.id"), index=True),
    Column("user_id", VARCHAR, nullable=False),
    Column("read_at", DateTime(timezone=True), nullable=False),
)

user = Table(
    "user",
    md_obj,
    Column("id", VARCHAR, primary_key=True),
    Column("firstseen", DateTime(timezone=True), nullable=False),
)

consent = Table(
    "consent",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("uid1", VARCHAR, nullable=False),
    Column("uid2", VARCHAR, nullable=False),
    Column("consentlevel", Integer, nullable=False),
    UniqueConstraint("uid1", "uid2"),
)

giveaways = Table(
    "giveaways",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("cid", VARCHAR, nullable=False),
    Column("mid", VARCHAR, nullable=False),
    Column("winners", Integer, nullable=False, default=1),
    Column("end", DateTime(timezone=True)),
    Column("expiry", DateTime(timezone=True), nullable=False),
)

giveaway_joins = Table(
    "giveaway_joins",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "gid",
        Integer,
        ForeignKey("giveaways.id"),
        nullable=False,
        comment="Giveaway ID",
    ),
    Column("uid", VARCHAR, nullable=False),
)

rp_counters = Table(
    "rp_counters",
    md_obj,
    Column("uid1", VARCHAR, primary_key=True),
    Column("uid2", VARCHAR, primary_key=True),
    Column("counter", VARCHAR, primary_key=True),
    Column("count", Integer, server_default="0", nullable=False),
)

web_tokens = Table(
    "web_tokens",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("gname", VARCHAR, nullable=False),
    Column("uid", VARCHAR, nullable=False),
    Column("uname", VARCHAR, nullable=False),
    Column("uavatar", VARCHAR, nullable=False),
    Column("token", VARCHAR, nullable=False),
    Column("expires", DateTime(timezone=True), nullable=False),
)

synced_channels = Table(
    "sync_channels",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("cname", VARCHAR, nullable=False),
    Column("ctype", VARCHAR, nullable=False, server_default="text"),
)

synced_roles = Table(
    "sync_roles",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("rid", VARCHAR, primary_key=True),
    Column("rname", VARCHAR, nullable=False),
)

synced_automod_rules = Table(
    "sync_automod_rules",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("aid", VARCHAR, primary_key=True),
    Column("aname", VARCHAR, nullable=False),
)

web_feedback_bans = Table(
    "web_feedback_bans", md_obj, Column("uid", VARCHAR, primary_key=True)
)

meow_back_settings = Table(
    "meow_back_settings",
    md_obj,
    Column("cid", VARCHAR, primary_key=True),
    Column("gid", VARCHAR, nullable=False),
    Column("meow", Integer, default=0),
    Column("waf", Integer, default=0),
    Column("bark", Integer, default=0),
    Column("colon_3", Integer, default=0),
    Column("owo", Integer, default=0),
    Column("awawa", Integer, default=0),
)

saves = Table(
    "saves",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("uid", VARCHAR, nullable=False),
    Column("link", VARCHAR, nullable=False),
)

suggestions = Table(
    "suggestions",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("author_id", VARCHAR, nullable=False),
    Column("message_id", VARCHAR, nullable=False),
)

suggestion_voting = Table(
    "suggestion_voting",
    md_obj,
    Column("message_id", VARCHAR, primary_key=True),
    Column("member_id", VARCHAR, primary_key=True),
    Column("vote", Integer, default=0),  # 0 downvote, 1 upvote
)
