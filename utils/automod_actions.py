import re
from datetime import timedelta

from discord import (
    AutoModActionExecutionEvent,
    AutoModRule,
    Bot,
    Embed,
    EmbedField,
    Guild,
    Message,
)
from sqlalchemy import Connection, select

from database import automod_actions, engine
from logger import akabot_logger
from utils.logs import send_message_to_log_channel
from utils.server_settings import KV


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


setting_automod_sync_error = KV(
    name="Automod actions sync error",
    default="",
)


async def handle_automod_action(
    c: Connection,
    payload: AutoModActionExecutionEvent,
    action: str,
    duration: str | None,
    content: str | None,
):
    if action == "kick":
        reason = content or "AutoMod action"

        await payload.member.kick(reason=reason)
        await send_message_to_log_channel(
            c,
            payload.guild,
            "automod_kick",
            Embed(
                title="Automod has Kicked a Member!",
                description="Akabot has kicked a member after AutoMod action execution",
                fields=[
                    EmbedField(
                        name="Member",
                        value=f"{payload.member.display_name} ({payload.member.name}; {payload.member.id})",
                    ),
                    EmbedField(name="Reason", value=reason),
                ],
            ),
        )
    elif action == "ban":
        reason = content or "AutoMod action"

        await payload.member.ban(reason=reason, delete_message_seconds=604800)
        await send_message_to_log_channel(
            c,
            payload.guild,
            "automod_ban",
            Embed(
                title="Automod has Banned a Member!",
                description="Akabot has banned a member after AutoMod action execution",
                fields=[
                    EmbedField(
                        name="Member",
                        value=f"{payload.member.display_name} ({payload.member.name}; {payload.member.id})",
                    ),
                    EmbedField(name="Reason", value=reason),
                ],
            ),
        )
    elif action == "mute":
        time = time_str_to_time(duration)

        reason = content or "Automod action"

        await payload.member.timeout_for(timedelta(seconds=time), reason=reason)
        await send_message_to_log_channel(
            c,
            payload.guild,
            "automod_mute",
            Embed(
                title="Automod has Muted a Member!",
                description="Akabot has muted a member after AutoMod action execution",
                fields=[
                    EmbedField(
                        name="Member",
                        value=f"{payload.member.display_name} ({payload.member.name}; {payload.member.id})",
                    ),
                    EmbedField(name="Reason", value=reason),
                    EmbedField(name="Duration of timeout", value=duration),
                ],
            ),
        )
    elif action == "dm":
        message = content or ""

        if payload.member.can_send(Message):
            await payload.member.send(content=message)
    else:
        akabot_logger.warning(
            f"Tried to perform action for {payload.rule_id}, but {action} is an invalid action!"
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
        actions = c.execute(
            select(
                automod_actions.c.action,
                automod_actions.c.duration,
                automod_actions.c.content,
            )
            .where(
                (automod_actions.c.gid == str(payload.guild.id))
                & (automod_actions.c.rule_id == str(payload.rule_id))
            )
            .order_by(automod_actions.c.id)
        ).fetchall()

    for i in actions:
        try:
            with (
                engine.begin() as c2
            ):  # separate connection for running this call with as an exception will not allow writing
                await handle_automod_action(c2, payload, i[0], i[1], i[2])
        except Exception as e:
            akabot_logger.exception(
                f"Failed to execute automod action for rule {payload.rule_id}: {e}"
            )
