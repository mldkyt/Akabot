import datetime

from discord import Message, Bot, HTTPException
from sqlalchemy import select, insert, update, delete

from database import engine, chat_revive
from logger import akabot_logger
from utils.server_settings import ServerSetting, SettingType

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
        setting = [i for i in setting_chat_revive_channels.get(c, message.guild.id) if
                   i.startswith(str(message.channel.id))]
        if len(setting) == 0:
            akabot_logger.debug("[Chat Revive] Event cancelled for %s #%s, not in chat revive", message.guild.name,
                                message.channel.name)
            return

        setting = setting[0]
        split = setting.split(";")
        minutes = split[1]  # we only care about the minutes because the channel id was filtered above

        existing = c.execute(
            select(chat_revive)
            .where((chat_revive.c.gid == str(message.guild.id)) & (chat_revive.c.cid == str(message.channel.id)))
        ).fetchone()

        if existing is None:
            c.execute(
                insert(chat_revive)
                .values(cid=str(message.channel.id), gid=str(message.guild.id),
                        notif_time=datetime.datetime.now() + datetime.timedelta(minutes=int(minutes)))
            )
            akabot_logger.debug("[Chat Revive] Added chat revive for %s #%s", message.guild.name, message.channel.name)
        else:
            c.execute(
                update(chat_revive)
                .values(notif_time=datetime.datetime.now() + datetime.timedelta(minutes=int(minutes)))
                .where((chat_revive.c.gid == str(message.guild.id)) & (chat_revive.c.cid == str(message.channel.id)))
            )
            akabot_logger.debug("[Chat Revive] Update chat revive for %s #%s", message.guild.name, message.channel.name)


async def notifications(bot: Bot):
    with engine.begin() as c:
        notifications = c.execute(
            select(chat_revive.c.gid, chat_revive.c.cid)
            .where(chat_revive.c.notif_time < datetime.datetime.now())
        ).fetchall()

        akabot_logger.debug("[Chat Revive] Sending %d notifications...", len(notifications))
        for i in notifications:
            try:
                guild = bot.get_guild(int(i[0]))
                channel = await bot.fetch_channel(int(i[1]))
                chat_revival_role = setting_chat_revive_role.get(c, guild.id)

                akabot_logger.debug("[Chat Revive] Sending in %s #%s...", guild.name, channel.name)
                if chat_revival_role is None:
                    await channel.send("Chat Revive!")
                else:
                    await channel.send(f"<@&{chat_revival_role}> Chat Revive!")
            except HTTPException:
                pass

        c.execute(
            delete(chat_revive)
            .where(chat_revive.c.notif_time < datetime.datetime.now())
        )
