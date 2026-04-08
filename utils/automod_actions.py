import re
from datetime import timedelta

from discord import (
    AutoModActionExecutionEvent,
    AutoModRule,
    Bot,
    Guild,
    Member,
    Message, Embed, EmbedField,
)
from sqlalchemy import Connection

from database import engine
from logger import nekona_logger
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


def process_add(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    args = v.split(",")

    if m.guild.id not in cached_automod_actions:
        return False, "No permission, or unable to fetch AutoMod rules"

    if len(args) < 2:
        return False, "There must be at least 2 parameters; e.g. rule name, action"

    rule = None
    for i in cached_automod_actions[m.guild.id]:
        if i.name == args[0].strip() and i.enabled:
            rule = i
            break
    if rule is None:
        return False, "The automod rule was not found"

    if args[1].strip() not in [
        "dm",
        "direct message",
        "pm",
        "private message",
        "kick",
        "ban",
        "mute",
        "timeout",
        "time out",
    ]:
        return False, "Action must be one of: dm, kick, ban, mute"

    ok = False
    err = ""

    if len(args) == 4:
        if args[1].strip() in ["timeout", "time out", "mute"]:
            time = time_str_to_time(args[2].strip())
            if time is None:
                return False, "Invalid time format, must be e.g. 1w, 12h, 4d"
            if time > 2419200:
                return False, "Date is outside of range"
            ok = True
    elif len(args) == 3:
        if args[1].strip() in [
            "dm",
            "direct message",
            "pm",
            "private message",
            "kick",
            "ban",
        ]:
            ok = True
        elif args[1].strip() in ["timeout", "time out", "mute"]:
            time = time_str_to_time(args[2].strip())
            if time is None:
                return False, "Invalid time format, must be e.g. 1w, 12h, 4d"
            if time > 2419200:
                return False, "Date is outside of range"
            ok = True
    elif len(args) == 2:
        if args[1].strip() in ["kick", "ban"]:
            ok = True

    if not ok:
        return False, f"Invalid amount of parameters for {args[1]}"

    if args[1] in ["mute", "timeout", "time out"]:
        action = "mute"
    elif args[1] in ["dm", "direct message", "pm", "private message"]:
        action = "dm"
    else:
        action = args[1]

    check_action = ["dm"]
    if action in ["mute", "kick", "ban"]:
        check_action = ["mute", "kick", "ban"]

    for i in automod_actions.get(c, m):
        i_args = i.split(";")
        if i_args[0] == str(rule.id) and i_args[1] in check_action:
            return False, (
                    f"There's already a `{i_args[1]}` rule, please remove that rule to add one of "
                    + ", ".join(check_action)
            )

    args = v.split(",")

    rule = None
    for i in cached_automod_actions[m.guild.id]:
        if i.name == args[0].strip() and i.enabled:
            rule = i
            break

    if args[1] in ["mute", "timeout", "time out"]:
        action = "mute"
    elif args[1] in ["dm", "direct message", "pm", "private message"]:
        action = "dm"
    else:
        action = args[1]

    return True, f"{rule.id};{action}" + (";" if len(args) > 2 else "") + ";".join(args[2:])


def process_remove(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    args = v.split(",")

    rule = None
    for i in cached_automod_actions[m.guild.id]:
        if args[0].strip().lower() in i.name.strip().lower():
            rule = i

    if len(args) == 1:
        for i in automod_actions.get(c, m):
            if i.startswith(str(rule.id)):
                break
        else:
            return False, "This rule was not found"
    else:
        # Transform action
        if args[1] in ["mute", "timeout", "time out"]:
            action = "mute"
        elif args[1] in ["dm", "direct message", "pm", "private message"]:
            action = "dm"
        else:
            action = args[1]

        for i in automod_actions.get(c, m):
            args_db = i.split(";")
            if (
                    args_db[0].strip().lower() == str(rule.id).strip().lower()
                    and args_db[1].strip().lower() == action
            ):
                break

        else:
            return False, "This rule was not found"

    args = v.split(",")

    rule = None
    for i in cached_automod_actions[m.guild.id]:
        if args[0].strip().lower() in i.name.strip().lower():
            rule = i

    if len(args) == 1:
        for i in automod_actions.get(c, m):
            if len(args) == 1:
                if i.startswith(str(rule.id)):
                    return True, i
    else:
        # Transform action
        if args[1] in ["mute", "timeout", "time out"]:
            action = "mute"
        elif args[1] in ["dm", "direct message", "pm", "private message"]:
            action = "dm"
        else:
            action = args[1]

        for i in automod_actions.get(c, m):
            args_db = i.split(";")
            if (
                    args_db[0].strip().lower() == str(rule.id).strip().lower()
                    and args_db[1].strip().lower() == action
            ):
                return True, i

    return True, v


cached_automod_actions: dict[int, list[AutoModRule]] = {}


async def fetch_actions(g: Guild):
    cached_automod_actions[g.id] = await g.fetch_auto_moderation_rules()


automod_actions = ServerSetting(
    name="Automod actions",
    description="A list of automod actions. Note that only one DM action and one kick/ban/mute action can be set at the same time. Format is usually `name of automod action, action to perform, action parameter(s) for adding to this setting, and `name of automod action, action to remove` for removing that action.",
    setting_type=SettingType.LIST,
    list_add_processor=process_add,
    list_remove_processor=process_remove,
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
            description='Nekona has kicked a member after AutoMod action execution',
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
            description='Nekona has banned a member after AutoMod action execution',
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
            description='Nekona has muted a member after AutoMod action execution',
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
        nekona_logger.warning(
            f"Tried to perform action for {payload.rule_id}, but {args[1]} is an invalid action!"
        )


async def handle_automod_actions(bot: Bot, payload: AutoModActionExecutionEvent):
    guild = payload.guild
    if guild is None:
        guild = await bot.fetch_guild(payload.guild_id)
        if guild is None:
            nekona_logger.warning(
                "When executing AutoMod actions, guild with ID %s was not found",
                str(payload.guild_id),
            )
            return

    member = payload.member
    if member is None:
        member = await guild.fetch_member(payload.user_id)
        if member is None:
            nekona_logger.warning(
                "When executing AutoMod actions in %s, member with ID %s was not found!",
                guild.name,
                str(payload.user_id),
            )
            return

    payload.guild = guild
    payload.member = member

    with engine.begin() as c:
        actions = automod_actions.get_guild(c, payload.guild)

    for i in actions:
        if i.startswith(str(payload.rule_id)):
            try:
                with engine.begin() as c2:  # separate connection for running this call with as an exception will not allow writing
                    await handle_automod_action(c2, payload, i)
            except Exception:
                nekona_logger.exception("AutoMod execution error occurred:")
