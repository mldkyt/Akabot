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


def validate_valid_format(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    # Check the format is valid (rule_name,action[,parameters])
    args = v.split(",")

    # Check cache
    if m.guild.id not in cached_automod_actions:
        return False, "No permission, or unable to fetch AutoMod rules"

    # Validate args count
    if len(args) < 2:
        return False, "There must be at least 2 parameters; e.g. rule name, action"

    # Validate rule name
    for i in cached_automod_actions[m.guild.id]:
        if i.name == args[0].strip() and i.enabled:
            rule = i
            break
    else:
        return False, "The automod rule was not found"

    # Validate action
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

    def check_parameters():
        # Validate parameters for dm, timeout
        if len(args) == 4:
            if args[1].strip() in [
                "timeout",
                "time out",
                "mute",
            ]:  # mute can have 4 parameters: rule_name, action, time, reason
                time = time_str_to_time(args[2].strip())
                if time is None:
                    return False, "Invalid time format, must be e.g. 1w, 12h, 4d"
                if time > 2419200:
                    return False, "Date is outside of range"
                return True, ""
        elif len(args) == 3:
            if args[1].strip() in [
                "dm",
                "direct message",
                "pm",
                "private message",
                "kick",
                "ban",
            ]:  # rule_name, action, dm/reason
                return True, ""
            elif args[1].strip() in [
                "timeout",
                "time out",
                "mute",
            ]:  # rule_name, action, time
                time = time_str_to_time(args[2].strip())
                if time is None:
                    return False, "Invalid time format, must be e.g. 1w, 12h, 4d"
                if time > 2419200:
                    return False, "Date is outside of range"
                return True, ""
        elif len(args) == 2:
            if args[1].strip() in ["kick", "ban"]:  # rule_name, action
                return True, ""

        return False, f"Invalid amount of parameters for {args[1]}"

    ok, err = check_parameters()
    if not ok:
        return False, err

    def check_database():
        if args[1] in ["mute", "timeout", "time out"]:
            action = "mute"
        elif args[1] in ["dm", "direct message", "pm", "private message"]:
            action = "dm"
        else:
            action = args[1]

        # Validate whether an action already exists
        # We only allow an instance of dm, and then one instance of either mute, kick or ban
        check_action = ["dm"]
        if action in ["mute", "kick", "ban"]:
            check_action = ["mute", "kick", "ban"]

        for i in automod_actions.get(c, m):
            i_args = i.split(";")
            if i_args[0] == str(rule.id) and i_args[1] in check_action:
                return False, f"There's already a `{i_args[1]}` rule, please remove that rule to add one of " + ', '.join(
                    check_action)

        return True, ""

    ok, err = check_database()
    if not ok:
        return False, err

    return True, ""


def transform_add(c: Connection, m: Member, v: str) -> str:
    args = v.split(",")

    rule = None
    # Transform name to id
    for i in cached_automod_actions[m.guild.id]:
        if i.name == args[0].strip() and i.enabled:
            rule = i
            break

    # Transform action
    if args[1] in ["mute", "timeout", "time out"]:
        action = "mute"
    elif args[1] in ["dm", "direct message", "pm", "private message"]:
        action = "dm"
    else:
        action = args[1]

    return f"{rule.id};{action}" + (";" if len(args) > 2 else "") + ";".join(args[2:])


def transform_remove(c: Connection, m: Member, v: str) -> str:
    args = v.split(",")

    rule = None
    for i in cached_automod_actions[m.guild.id]:
        if args[0].strip().lower() in i.name.strip().lower():
            rule = i

    if len(args) == 1:
        for i in automod_actions.get(c, m):
            if len(args) == 1:
                if i.startswith(str(rule.id)):
                    return i
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
                return i

    return v


def validate_remove(c: Connection, m: Member, v: str) -> tuple[bool, str]:
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

    return True, ""


cached_automod_actions: dict[int, list[AutoModRule]] = {}


async def fetch_actions(g: Guild):
    cached_automod_actions[g.id] = await g.fetch_auto_moderation_rules()


automod_actions = ServerSetting(
    name="Automod actions",
    setting_type=SettingType.LIST,
    list_add_validator=validate_valid_format,
    list_add_transformer=transform_add,
    list_remove_validator=validate_remove,
    list_remove_transformer=transform_remove,
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
        actions = automod_actions.get_direct(c, payload.guild)

    for i in actions:
        if i.startswith(str(payload.rule_id)):
            try:
                with engine.begin() as c2:  # separate connection for running this call with as an exception will not allow writing
                    await handle_automod_action(c2, payload, i)
            except Exception:
                nekona_logger.exception("AutoMod execution error occurred:")
