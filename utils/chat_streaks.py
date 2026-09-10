import datetime
from datetime import date, timedelta

import sentry_sdk
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

from database import chat_streaks, engine
from utils.bot_channel import setting_bot_channel
from utils.server_settings import ServerSetting, SettingType
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


user_setting_receive_notifications = UserSetting(
    name="Remind about chat streaks in DM's", default="false"
)


def update_for_user(c: Connection, u: Member):
    """Update chat streaks for a member"""

    now = date.today()
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

    now = date.today()

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

    return (datetime.datetime.now(datetime.UTC).date() - start_date).days


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

    return [i for i in a if (date.today() - i[2]).total_seconds() <= 86400]


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

    today = datetime.datetime.now(datetime.UTC).date()
    for streak in streaks:
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
        sentry_sdk.capture_exception(e)
        return None, False
