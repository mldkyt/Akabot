import datetime

from discord import Message, Member, Bot, HTTPException
from sqlalchemy import Connection, select, insert, update, delete

from database import engine, chat_revive
from logger import akabot_logger
from utils.server_settings import ServerSetting, SettingType, setting_to_text_channel, setting_to_number, \
    setting_simple_string, setting_to_role


def chat_revive_add(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    # Param check
    args = v.split(",")
    if len(args) != 2:
        return False, "Invalid amount of parameters"

    args = [arg.strip() for arg in args]

    ok, channel_id = setting_to_text_channel(c, m, args[0])
    if not ok:
        return ok, channel_id

    existing = [i for i in setting_chat_revive_channels.get(c, m.guild.id) if i.startswith(channel_id)]
    if len(existing) != 0:
        # TODO update list element inside of settings for this case
        return False, "This channel is already a chat revive channel, to update minutes count, please remove and re-add"

    ok, minutes = setting_to_number(c, m, args[1])
    if not ok:
        return ok, minutes

    return True, f"{channel_id};{minutes}"


def chat_revive_remove(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    ok, channel_id = setting_to_text_channel(c, m, v)
    if not ok:
        return False, channel_id

    existing = [i for i in setting_chat_revive_channels.get(c, m.guild.id) if i.startswith(channel_id)]
    if len(existing) == 0:
        return False, "This channel is not a chat revive channel"

    return True, existing[0]


def chat_revive_view(c: Connection, m: Member, v: list[str]) -> str:
    if len(v) == 0:
        return "Chat revive channel list: None"

    items = []
    for i in v:
        j = i.split(";")
        items.append(f"<@&{j[0]}>: {j[1]} minutes")
    return "Chat revive channel list: " + ", ".join(items)


def chat_revive_response(c: Connection, m: Member, v: str) -> str:
    i = v.split(";")

    return f"Added channel <#{i[0]}> with {i[1]} minutes to chat remove"


def chat_revive_response_remove(c: Connection, m: Member, v: str) -> str:
    i = v.split(";")

    return f"Removed channel <#{i[0]}> from chat revive"


setting_chat_revive_channels = ServerSetting(
    name="Chat Revive Channels",
    description="List of channels that should be in the chat revive. Syntax: \"channel, minutes\". Channel can be a mention, ID or name. Minutes is amount of minutes before a chat revive triggers.",
    setting_type=SettingType.LIST,
    list_add_processor=chat_revive_add,
    list_remove_processor=chat_revive_remove,
    list_view=chat_revive_view,
    list_add_response=chat_revive_response,
    list_remove_response=chat_revive_response_remove
)
setting_chat_revive_role = ServerSetting(
    name="Chat Revive Role",
    description="Role to ping when chat revive triggers.",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_role,
    normal_view=setting_simple_string("Chat revival ping role: <@&%s>"),
    normal_response=setting_simple_string("Set chat revival ping role to <@&%s>")
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
