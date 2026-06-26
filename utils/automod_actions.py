import re
from datetime import timedelta

from discord import (
    AutoModActionExecutionEvent,
    AutoModRule,
    Bot,
    Guild,
    Message, Embed, EmbedField,
)
from sqlalchemy import Connection

from database import engine
from logger import akabot_logger
from utils.logs import send_message_to_log_channel
from utils.server_settings import ServerSetting, SettingType


def time_str_to_time(time: str):
    if not re.match("^[0-9]{1,2}[hdw]$", time):
        return None

    if time.endswith("h"):
        return 3600 * int(time[:-1])
    elif time.endswith("d"):
        return 86400 * int(time[:-1])
    else:
        return 604800 * int(time[:-1])

cached_automod_actions: dict[int, list[AutoModRule]] = {}


async def fetch_actions(g: Guild):
    cached_automod_actions[g.id] = await g.fetch_auto_moderation_rules()


automod_actions = ServerSetting(
    name="Automod actions",
    setting_type=SettingType.LIST
)


async def handle_automod_action(c: Connection, payload: AutoModActionExecutionEvent, rule: str):
    args = rule.split(";")

    if args[1] == "kick":
        reason = "AutoMod action"
        if len(args) > 3:
            reason = ";".join(args[2:])

        await payload.member.kick(reason=reason)
        await send_message_to_log_channel(c, payload.guild, Embed(
            title='Automod has Kicked a Member!',
            description='Akabot has kicked a member after AutoMod action execution',
            fields=[
                EmbedField(name="Member",
                           value=f"{payload.member.display_name} ({payload.member.name}; {payload.member.id})"),
                EmbedField(name="Reason", value=reason)
            ]
        ))
    elif args[1] == "ban":
        reason = "AutoMod action"
        if len(args) > 3:
            reason = ";".join(args[2:])

        await payload.member.ban(reason=reason, delete_message_seconds=604800)
        await send_message_to_log_channel(c, payload.guild, Embed(
            title='Automod has Banned a Member!',
            description='Akabot has banned a member after AutoMod action execution',
            fields=[
                EmbedField(name="Member",
                           value=f"{payload.member.display_name} ({payload.member.name}; {payload.member.id})"),
                EmbedField(name="Reason", value=reason)
            ]
        ))
    elif args[1] == "mute":
        time = time_str_to_time(args[2])

        reason = "Automod action"
        if len(args) > 4:
            reason = ";".join(args[3:])

        await payload.member.timeout_for(timedelta(seconds=time), reason=reason)
        await send_message_to_log_channel(c, payload.guild, Embed(
            title='Automod has Muted a Member!',
            description='Akabot has muted a member after AutoMod action execution',
            fields=[
                EmbedField(name="Member",
                           value=f"{payload.member.display_name} ({payload.member.name}; {payload.member.id})"),
                EmbedField(name="Reason", value=reason),
                EmbedField(name="Duration of timeout", value=args[2])
            ]
        ))
    elif args[1] == "dm":
        message = ";".join(args[2:])

        if payload.member.can_send(Message):
            await payload.member.send(content=message)
    else:
        akabot_logger.warning(
            f"Tried to perform action for {payload.rule_id}, but {args[1]} is an invalid action!"
        )


async def handle_automod_actions(bot: Bot, payload: AutoModActionExecutionEvent):
    guild = payload.guild
    if guild is None:
        guild = await bot.fetch_guild(payload.guild_id)
        if guild is None:
            akabot_logger.warning(
                "When executing AutoMod actions, guild with ID %s was not found",
                str(payload.guild_id),
            )
            return

    member = payload.member
    if member is None:
        member = await guild.fetch_member(payload.user_id)
        if member is None:
            akabot_logger.warning(
                "When executing AutoMod actions in %s, member with ID %s was not found!",
                guild.name,
                str(payload.user_id),
            )
            return

    payload.guild = guild
    payload.member = member

    with engine.begin() as c:
        actions = automod_actions.get(c, payload.guild.id)

    for i in actions:
        if i.startswith(str(payload.rule_id)):
            try:
                with engine.begin() as c2:  # separate connection for running this call with as an exception will not allow writing
                    await handle_automod_action(c2, payload, i)
            except Exception:
                akabot_logger.exception("AutoMod execution error occurred:")
