import sentry_sdk
from datetime import timedelta

from discord import (
    Bot,
    DMChannel,
    Guild,
    Member,
    Message,
    PartialMessageable,
    TextChannel,
)
from discord.ui import BaseView
from sqlalchemy import Connection, desc, insert, select, update

from database import chat_streak_last_members, chat_streaks, engine
from logger import akabot_logger
from utils.bot_channel import setting_bot_channel
from utils.server_settings import ServerSetting, SettingType
from utils.timezones import get_now
from utils.user_settings import UserSetting

server_response_setting = ServerSetting(
    "Chat streaks response setting",
    setting_type=SettingType.NORMAL,
    default="on",
)

user_response_setting = UserSetting(
    "Chat streaks response setting",
    setting_type=SettingType.NORMAL,
    default="on",
)

server_message_delay = ServerSetting(
    "Chat streaks message duration",
    setting_type=SettingType.NORMAL,
    default="5",
)

server_streak_minimum_enabled = ServerSetting(
    "Chat streaks minimum enabled",
    setting_type=SettingType.NORMAL,
    default="false",
)

server_streak_minimum = ServerSetting(
    "Chat streaks minimum messages",
    setting_type=SettingType.NORMAL,
    default="5",
)

server_streak_same_member_check = ServerSetting(
    "Chat streaks same member check",
    setting_type=SettingType.NORMAL,
    default="false",
)


user_setting_receive_notifications = UserSetting(
    name="Remind about chat streaks in DM's", default="false"
)


def update_for_user(c: Connection, u: Member):
    """Update chat streaks for a member"""

    now = get_now(u.guild.id, c).date()
    yesterday = now - timedelta(days=1)

    # Check if we have an existant chat streak
    a = c.execute(
        select(chat_streaks.c.start_date, chat_streaks.c.last_message_date).where(
            (chat_streaks.c.uid == str(u.id)) & (chat_streaks.c.gid == str(u.guild.id))
        )
    ).fetchone()

    if a is None:
        c.execute(
            insert(chat_streaks).values(
                gid=str(u.guild.id),
                uid=str(u.id),
                start_date=yesterday,
                last_message_date=now,
            )
        )
    else:
        # Check days split
        start_date = a[0]
        last_message_date = a[1]
        diff = now - last_message_date

        if diff.days > 1:
            # Failed!
            c.execute(
                update(chat_streaks)
                .where(
                    (chat_streaks.c.uid == str(u.id))
                    & (chat_streaks.c.gid == str(u.guild.id))
                )
                .values(start_date=yesterday, last_message_date=now)
            )
        elif diff.days == 0 and start_date == now:
            c.execute(
                update(chat_streaks)
                .where(
                    (chat_streaks.c.uid == str(u.id))
                    & (chat_streaks.c.gid == str(u.guild.id))
                )
                .values(start_date=yesterday)
            )
        elif diff.days == 1:
            # Update
            c.execute(
                update(chat_streaks)
                .where(
                    (chat_streaks.c.uid == str(u.id))
                    & (chat_streaks.c.gid == str(u.guild.id))
                )
                .values(last_message_date=now)
            )


def get_streak(c: Connection, u: Member):
    """Get streak"""

    now = get_now(u.guild.id, c).date()

    a = c.execute(
        select(chat_streaks.c.start_date, chat_streaks.c.last_message_date).where(
            (chat_streaks.c.uid == str(u.id)) & (chat_streaks.c.gid == str(u.guild.id))
        )
    ).fetchone()

    if a is None:
        return 0

    start_date = a[0]
    last_message_date = a[1]

    if (now - last_message_date).days > 1:
        return 0

    return (last_message_date - start_date).days


def get_message_count(c: Connection, u: Member):
    """Get the amount of counted messages sent today"""
    now = get_now(u.guild.id, c).date()

    a = c.execute(
        select(chat_streaks.c.message_count, chat_streaks.c.message_count_date).where(
            (chat_streaks.c.uid == str(u.id)) & (chat_streaks.c.gid == str(u.guild.id))
        )
    ).fetchone()

    if a is None or a[1] != now:
        return 0

    return a[0] or 0


def count_message(c: Connection, u: Member, cid: int, same_member_check: bool):
    """Count a message toward the daily minimum. Returns the updated count."""
    today = get_now(u.guild.id, c).date()
    gid = str(u.guild.id)
    uid = str(u.id)
    cid = str(cid)

    if same_member_check:
        a = c.execute(
            select(chat_streak_last_members.c.uid).where(
                (chat_streak_last_members.c.gid == gid)
                & (chat_streak_last_members.c.cid == cid)
                & (chat_streak_last_members.c.date == today)
            )
        ).fetchone()

        if a is not None:
            if a[0] == uid:
                return get_message_count(c, u)

            c.execute(
                update(chat_streak_last_members)
                .values(uid=uid)
                .where(
                    (chat_streak_last_members.c.gid == gid)
                    & (chat_streak_last_members.c.cid == cid)
                    & (chat_streak_last_members.c.date == today)
                )
            )
        else:
            c.execute(
                insert(chat_streak_last_members).values(
                    gid=gid, cid=cid, date=today, uid=uid
                )
            )

    a = c.execute(
        select(
            chat_streaks.c.start_date,
            chat_streaks.c.last_message_date,
            chat_streaks.c.message_count,
            chat_streaks.c.message_count_date,
        ).where((chat_streaks.c.uid == uid) & (chat_streaks.c.gid == gid))
    ).fetchone()

    if a is None:
        c.execute(
            insert(chat_streaks).values(
                gid=gid,
                uid=uid,
                start_date=today,
                last_message_date=today,
                message_count=1,
                message_count_date=today,
            )
        )
        return 1

    if a[3] == today:
        new_count = (a[2] or 0) + 1
    else:
        new_count = 1

    c.execute(
        update(chat_streaks)
        .values(message_count=new_count, message_count_date=today)
        .where((chat_streaks.c.uid == uid) & (chat_streaks.c.gid == gid))
    )
    return new_count


def get_unexpired_streak(c: Connection, u: Member):
    """Get streak"""
    a = c.execute(
        select(chat_streaks.c.start_date, chat_streaks.c.last_message_date).where(
            (chat_streaks.c.uid == str(u.id)) & (chat_streaks.c.gid == str(u.guild.id))
        )
    ).fetchone()

    if a is None:
        return 0

    start_date = a[0]
    last_message_date = a[1]

    return (last_message_date - start_date).days


def get_raw_streak(c: Connection, u: Member):
    """Get raw streak"""
    a = c.execute(
        select(chat_streaks.c.start_date).where(
            (chat_streaks.c.uid == str(u.id)) & (chat_streaks.c.gid == str(u.guild.id))
        )
    ).fetchone()

    if a is None:
        return 0

    start_date = a[0]

    return (get_now(u.guild.id, c).date() - start_date).days


def get_leaderboard(c: Connection, u: Member):
    """Leaderboard"""

    a = c.execute(
        select(
            chat_streaks.c.uid,
            chat_streaks.c.start_date,
            chat_streaks.c.last_message_date,
        )
        .where(chat_streaks.c.gid == str(u.guild.id))
        .order_by(desc(chat_streaks.c.last_message_date - chat_streaks.c.start_date))
    ).fetchall()

    return [i for i in a if (get_now(u.guild.id, c).date() - i[2]).total_seconds() <= 86400]


def get_all_streaks_for(c: Connection, b: Bot, m: Member):
    a = c.execute(
        select(
            chat_streaks.c.gid,
            chat_streaks.c.start_date,
            chat_streaks.c.last_message_date,
        )
        .where(chat_streaks.c.gid == str(m.guild.id))
        .order_by(desc(chat_streaks.c.last_message_date - chat_streaks.c.start_date))
    ).fetchall()

    return a


async def get_expiring_streaks(c: Connection):
    streaks = c.execute(
        select(chat_streaks.c.gid, chat_streaks.c.uid, chat_streaks.c.last_message_date)
    ).fetchall()

    for streak in streaks:
        today = get_now(int(streak[0]), c).date()
        if (today - streak[2]).days == 1:
            yield (streak[0], streak[1])


def get_guild_link(g: Guild):
    for i in g.text_channels:
        p = i.permissions_for(g.default_role)
        if p.view_channel and p.read_messages:
            return i

    return None


async def handle_send_reply(
    msg: Message, content: str, view: BaseView | None = None
) -> tuple[Message | None, bool]:
    """Handle send reply. Posts inside of bot channel or into the same channel. Returns true if posted into the same channel."""
    try:
        assert msg.guild is not None
        assert not isinstance(msg.channel, PartialMessageable) and not isinstance(
            msg.channel, DMChannel
        )

        with engine.begin() as c:
            bot_channel_id = setting_bot_channel.get(c, msg.guild.id)
            setting_response = server_response_setting.get(c, msg.guild.id)

        if setting_response == "off":
            return None, False

        bot_channel = (
            msg.guild.get_channel(int(bot_channel_id)) if bot_channel_id != "" else None
        )

        chan_perm = msg.channel.permissions_for(msg.guild.me)
        if chan_perm.read_message_history and chan_perm.send_messages:
            if len(bot_channel_id.strip()) == 0:
                if setting_response == "on":
                    return await msg.reply(content, view=view), True

            if bot_channel is None:
                if setting_response == "on":
                    return await msg.reply(content, view=view), True

        if "bot" not in setting_response:
            return None, False

        if bot_channel is None:
            return None, False

        assert isinstance(bot_channel, TextChannel)
        if not bot_channel.permissions_for(msg.guild.me).send_messages:
            return None, False

        if setting_response != "bot_noping":
            content = f"{msg.author.mention} {content}"

        return await bot_channel.send(content, view=view), False
    except Exception as e:
        akabot_logger.exception(f"Failed to send chat streak response for message {msg.id}: {e}")
        sentry_sdk.capture_exception(e)
        return None, False
