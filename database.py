import json
import os.path

from sqlalchemy import (
    DATE,
    DECIMAL,
    VARCHAR,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    StaticPool,
    Table,
    UniqueConstraint,
    Boolean,
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

kv = Table(
    "kv",
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

user_settings_list = Table(
    "user_settings_list",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("uid", VARCHAR),
    Column("name", VARCHAR),
    Column("value", VARCHAR),
    UniqueConstraint("uid", "name", "value"),
)

leveling = Table(
    "leveling",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("gid", VARCHAR, primary_key=True),
    Column("xp", Integer),
)

leveling_rewards = Table(
    "leveling_rewards",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("rid", VARCHAR, nullable=False),
    Column("level", Integer, nullable=False),
    UniqueConstraint("gid", "rid"),
)

leveling_multipliers = Table(
    "leveling_multipliers",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("start_month", Integer, nullable=False),
    Column("start_day", Integer, nullable=False),
    Column("end_month", Integer, nullable=False),
    Column("end_day", Integer, nullable=False),
    Column("multiplier", Integer, nullable=False),
)

moderator_roles = Table(
    "moderator_roles",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("rid", VARCHAR, nullable=False),
    UniqueConstraint("gid", "rid"),
)

roles_on_join = Table(
    "roles_on_join",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("rid", VARCHAR, nullable=False),
    UniqueConstraint("gid", "rid"),
)

statistic_channels = Table(
    "statistic_channels",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("cid", VARCHAR, nullable=False),
    Column("template", VARCHAR, nullable=False),
    UniqueConstraint("gid", "cid"),
)

suggestion_channels = Table(
    "suggestion_channels",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("cid", VARCHAR, nullable=False),
    UniqueConstraint("gid", "cid"),
)

temporary_vc_creator_channels = Table(
    "temporary_vc_creator_channels",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("cid", VARCHAR, nullable=False),
    UniqueConstraint("gid", "cid"),
)

# Chat Summary

chat_summary_channels = Table(
    "chat_summary_channel",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("messages", Integer),
    Column("last_member", VARCHAR, default="0", server_default="0", nullable=False),
)

chat_summary_members = Table(
    "chat_summary_members",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("messages", Integer),
    Column("last_message", DateTime(timezone=True)),
)

monthly_chat_summary_channels = Table(
    "chat_summary_channel_monthly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("messages", Integer),
    Column("last_member", VARCHAR, default="0", server_default="0", nullable=False),
)

monthly_chat_summary_members = Table(
    "chat_summary_members_monthly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("messages", Integer),
    Column("last_message", DateTime(timezone=True)),
)

yearly_chat_summary_channels = Table(
    "chat_summary_channel_yearly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("messages", Integer),
    Column("last_member", VARCHAR, default="0", server_default="0", nullable=False),
)

yearly_chat_summary_members = Table(
    "chat_summary_members_yearly",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("messages", Integer),
    Column("last_message", DateTime(timezone=True)),
)

past_chat_summaries = Table(
    "past_chat_summaries",
    md_obj,
    Column("id", VARCHAR, primary_key=True),
    Column("gid", VARCHAR, nullable=False),
    Column("cid", VARCHAR, nullable=False),
    Column("kind", VARCHAR, nullable=False),
    Column("period", VARCHAR, nullable=False),
    Column("total_messages", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

past_chat_summaries_rows = Table(
    "past_chat_summaries_rows",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("summary_id", VARCHAR, ForeignKey("past_chat_summaries.id", ondelete="CASCADE"), nullable=False),
    Column("uid", VARCHAR, nullable=False),
    Column("messages", Integer, nullable=False),
    Column("rank", Integer, nullable=False),
)

chat_streaks = Table(
    "chat_streaks",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("start_date", DATE, nullable=False),
    Column("last_message_date", DATE, nullable=False),
    Column("message_count", Integer, nullable=False, server_default="0"),
    Column("message_count_date", DATE),
)

chat_streak_last_members = Table(
    "chat_streak_last_members",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("cid", VARCHAR, primary_key=True),
    Column("date", DATE, primary_key=True),
    Column("uid", VARCHAR, nullable=False),
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

chat_revive_channels = Table(
    "chat_revive_channels",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("cid", VARCHAR, nullable=False),
    Column("minutes", Integer, nullable=False),
    UniqueConstraint("gid", "cid"),
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

automod_actions = Table(
    "automod_actions",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("rule_id", VARCHAR, nullable=False),
    Column("action", VARCHAR, nullable=False),
    Column("duration", VARCHAR),
    Column("content", VARCHAR),
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

sticky_messages = Table(
    "sticky_messages",
    md_obj,
    Column("channel_id", VARCHAR, primary_key=True),
    Column("guild_id", VARCHAR, nullable=False),
    Column("content", VARCHAR, nullable=False),
    Column("last_msg_id", VARCHAR),
    Column("cooldown", DateTime(timezone=True)),
)

periodic_messages = Table(
    "periodic_messages",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("channel_id", VARCHAR, nullable=False),
    Column("guild_id", VARCHAR, nullable=False),
    Column("period", VARCHAR, nullable=False, default="daily"),
    Column("period_num", Integer, nullable=False, default=0),
    Column("next_send", DateTime(timezone=True)),
    Column("content", VARCHAR, nullable=False),
)

# Add this new table to the existing declarations
markov = Table(
    "markov",
    md_obj,
    Column("channel_id", VARCHAR, primary_key=True),
    Column("guild_id", VARCHAR, nullable=False),
    Column("mode", VARCHAR, nullable=False, server_default="periodic"),
    Column("period", VARCHAR, default="daily"),
    Column("period_num", Integer, default=1),
    Column("next_send", DateTime(timezone=True)),
    Column("messages_sent_since", Integer, nullable=False, server_default="0"),
    Column("messages_num", Integer, nullable=False, server_default="0"),
)

tags = Table(
    "tags",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("guild_id", VARCHAR, nullable=False),
    Column("keyword", VARCHAR, nullable=False),
    Column("content", VARCHAR, nullable=False),
)


message_counting = Table(
    "message_counting",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("name", VARCHAR),
    Column("messages", Integer),
)

message_counting_members = Table(
    "message_counting_members",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("uid", VARCHAR, primary_key=True),
    Column("name", VARCHAR),
    Column("messages", Integer),
)

message_counting_rewards = Table(
    "message_counting_rewards",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("messages", Integer, nullable=False),
    Column("type", VARCHAR, nullable=False),
    Column("rid", VARCHAR),
    Column("multiplier", DECIMAL),
)

verification_introduction_messages = Table(
    "verification_introduction_messages",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("guild_id", VARCHAR, nullable=False),
    Column("author_id", VARCHAR, nullable=False),
    Column("admin_message_id", VARCHAR, nullable=False),
    Column("introduction_message_id", VARCHAR, nullable=False),
)

logging_channels = Table(
    "logging_channels",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("cid", VARCHAR, nullable=False),
    Column("type", VARCHAR, nullable=False),
)

vote_points = Table(
    "vote_points",
    md_obj,
    Column("uid", VARCHAR, primary_key=True),
    Column("points", Integer, nullable=False, default="0"),
    Column("last_vote", DateTime),
)

# Tasks

tasks = Table(
    "tasks",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("direction", VARCHAR, nullable=False),
    Column("type", VARCHAR, nullable=False),
    Column("data", VARCHAR, nullable=False),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("next_attempt", DateTime(timezone=True)),
    Column("error", VARCHAR),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

# Reaction Roles

reaction_roles = Table(
    "reaction_roles",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("gid", VARCHAR, nullable=False),
    Column("cid", VARCHAR, nullable=False),
    Column("mid", VARCHAR),
    Column("type", VARCHAR, nullable=False, server_default="n"),
    Column("content", VARCHAR),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

reaction_roles_options = Table(
    "reaction_roles_options",
    md_obj,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column(
        "rr_id",
        Integer,
        ForeignKey("reaction_roles.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("position", Integer, nullable=False, server_default="0"),
    Column("style", VARCHAR, nullable=False, server_default="primary"),
    Column("label", VARCHAR),
    Column("emoji", VARCHAR),
    Column("rid", VARCHAR, nullable=False),
    UniqueConstraint("rr_id", "rid"),
)

synced_emojis = Table(
    "synced_emojis",
    md_obj,
    Column("gid", VARCHAR, primary_key=True),
    Column("eid", VARCHAR, primary_key=True),
    Column("name", VARCHAR, nullable=False),
    Column("animated", Boolean, nullable=False, server_default="0"),
)
