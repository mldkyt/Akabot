import datetime

from discord import Bot, HTTPException, Message
from sqlalchemy import delete, insert, select, update

from database import chat_revive, engine
from logger import akabot_logger
from utils.server_settings import ServerSetting, SettingType
from utils.timezones import get_now

setting_chat_revive_channels = ServerSetting(
    name="Chat Revive Channels",
    setting_type=SettingType.LIST,
)
setting_chat_revive_role = ServerSetting(
    name="Chat Revive Role",
    setting_type=SettingType.NORMAL,
)


async def update_chat_revive(message: Message):
    if message.author.bot:
        return

    with engine.begin() as c:
        setting = [
            i
            for i in setting_chat_revive_channels.get(c, message.guild.id)
            if i.split(";", 1)[0] == str(message.channel.id)
        ]
        if len(setting) == 0:
            return

        setting = setting[0]
        split = setting.split(";")
        minutes = split[
            1
        ]  # we only care about the minutes because the channel id was filtered above

        existing = c.execute(
            select(chat_revive).where(
                (chat_revive.c.gid == str(message.guild.id))
                & (chat_revive.c.cid == str(message.channel.id))
            )
        ).fetchone()

        if existing is None:
            c.execute(
                insert(chat_revive).values(
                    cid=str(message.channel.id),
                    gid=str(message.guild.id),
                    notif_time=get_now(message.guild.id, c)
                    + datetime.timedelta(minutes=int(minutes)),
                )
            )
        else:
            c.execute(
                update(chat_revive)
                .values(
                    notif_time=get_now(message.guild.id, c)
                    + datetime.timedelta(minutes=int(minutes))
                )
                .where(
                    (chat_revive.c.gid == str(message.guild.id))
                    & (chat_revive.c.cid == str(message.channel.id))
                )
            )


async def notifications(bot: Bot):
    with engine.begin() as c:
        notifications = c.execute(
            select(chat_revive.c.gid, chat_revive.c.cid, chat_revive.c.notif_time)
        ).fetchall()

        expired = [
            i for i in notifications if i[2] < get_now(int(i[0]), c)
        ]

        for i in expired:
            try:
                guild = bot.get_guild(int(i[0]))
                if guild is None:
                    continue
                channel = await bot.fetch_channel(int(i[1]))
                chat_revival_role = setting_chat_revive_role.get(c, guild.id)

                if chat_revival_role is None:
                    await channel.send("Chat Revive!")
                else:
                    await channel.send(f"<@&{chat_revival_role}> Chat Revive!")
            except HTTPException:
                akabot_logger.warning(
                    f"Failed to send chat revive message in channel {i[1]} of guild {i[0]}"
                )

        for i in expired:
            c.execute(
                delete(chat_revive).where(
                    (chat_revive.c.gid == i[0]) & (chat_revive.c.cid == i[1])
                )
            )
