import re
from datetime import datetime

import discord
from discord import Member
from sqlalchemy import Connection, insert, select, update

from database import leveling, server_settings_list
from logger import nekona_logger
from utils.conversion import convert_role
from utils.server_settings import (
    ServerSetting,
    SettingType,
    setting_is_boolean,
    setting_is_number,
    setting_simple_string,
    setting_simple_string_boolean,
    setting_to_boolean,
)


# noinspection PyUnusedLocal
def add_reward_validator(c: Connection, member: Member, value: str) -> tuple[bool, str]:
    split = value.split(",")
    if len(split) < 2:
        return (
            False,
            "Invalid amount of parameters for a role reward, the syntax is `<role mention, name or ID>, <level>` (mind the comma).",
        )

    role_id = split[0].strip()
    level = split[1].strip()
    index = split[2] if len(split) > 2 else "0"

    if index.isnumeric():
        index = int(index)
    else:
        index = 0

    # Check the role
    role = convert_role(member.guild, role_id, index)

    if role is None:
        return False, "Role was not fond"

    if not level.isnumeric():
        return False, "The level number is not a number"

    return True, ""


# noinspection PyUnusedLocal
def add_reward_transformer(c: Connection, member: Member, value: str) -> str:
    split = value.split(",")
    if len(split) < 2:
        raise ValueError("Invalid amount of parameters was entered into the command")

    role_id = split[0].strip()
    level = split[1].strip()
    index = split[2] if len(split) > 2 else "0"

    if index.isnumeric():
        index = int(index)
    else:
        index = 0

    # Check the role
    role = convert_role(member.guild, role_id, index)

    if role is None:
        raise ValueError("The role was not found")

    if not level.isnumeric():
        raise ValueError("The level required is not a numeric value")

    return f"{role.id};{level}"


# noinspection PyUnusedLocal
def add_reward_response(c: Connection, member: Member, value: str):
    split = value.split(";")

    return f"Added level-up reward for <@&{split[0]}> for level {split[1]}"


def remove_reward_validator(
    c: Connection, member: Member, value: str
) -> tuple[bool, str]:
    split = value.split(",")

    role_id = split[0].strip()
    index = split[1] if len(split) > 1 else "0"

    if index.isnumeric():
        index = int(index)
    else:
        index = 0

    # Check the role
    role = convert_role(member.guild, role_id, index)

    if role is None:
        return False, "Role was not found"

    db_record = c.execute(
        select(server_settings_list.c.value).where(
            (server_settings_list.c.value.like("{};%".format(role.id)))
            & (server_settings_list.c.uid == str(member.guild.id))
            & (server_settings_list.c.name == "Leveling rewards")
        )
    ).fetchone()

    if db_record is None:
        return False, "This role is not in rewards"

    return True, ""


def remove_reward_transformer(c: Connection, member: Member, value: str) -> str:
    split = value.split(",")

    role_id = split[0].strip()
    index = split[1] if len(split) > 1 else "0"

    if index.isnumeric():
        index = int(index)
    else:
        index = 0

    # Check the role
    role = convert_role(member.guild, role_id, index)

    if role is None:
        raise ValueError("The role was not found")

    db_record = c.execute(
        select(server_settings_list.c.value).where(
            (server_settings_list.c.value.like("{};%".format(role.id)))
            & (server_settings_list.c.uid == str(member.guild.id))
            & (server_settings_list.c.name == "Leveling rewards")
        )
    ).fetchone()

    if db_record is not None:
        return f"{db_record[0]}"

    raise ValueError(f"Role not found in DB for {role.id} ({role.name})")


def get_reward_view(c: Connection, m: Member, val: list[str]) -> str:
    if len(val) == 0:
        return "Empty"

    converted = []

    for i in val:
        split = i.split(";")
        role = convert_role(m.guild, split[0])

        if role is None:
            continue

        converted.append(f"role {role.mention} is rewarded at level {split[1]}")

    return "Leveling rewards: " + ", ".join(converted)


def add_multiplier_validator(c: Connection, m: Member, s: str) -> tuple[bool, str]:
    output = re.match(r"^(\d+)-(\d+) +- +(\d+)-(\d+), +(\d)$", s.strip())
    if not output:
        return (
            False,
            "Invalid format for a multiplier. Format is `<MM>-<DD> - <MM>-<DD>, <Multiplier>`",
        )

    out_groups = output.groups()
    start_month, start_day = (int(out_groups[0]), int(out_groups[1]))
    end_month, end_day = (int(out_groups[2]), int(out_groups[3]))
    multiplier = int(out_groups[4])

    try:
        start_date = datetime(2024, start_month, start_day)
    except Exception:
        return False, "Invalid start date"

    try:
        end_date = datetime(2024, end_month, end_day)
    except Exception:
        return False, "Invalid end date"

    # Shift for over-year events (such as 12-23 - 01-03)
    if start_date > end_date:
        try:
            end_date = datetime(2025, end_month, end_day)
        except Exception:
            return False, "Invalid end date"

    if multiplier < 1:
        return False, "Invalid multiplier"

    return True, ""


def add_multiplier_transformer(c: Connection, m: Member, s: str) -> str:
    output = re.match(r"^(\d+)-(\d+) +- +(\d+)-(\d+), +(\d)$", s.strip())

    out_groups = output.groups()
    start_month, start_day = (int(out_groups[0]), int(out_groups[1]))
    end_month, end_day = (int(out_groups[2]), int(out_groups[3]))
    multiplier = int(out_groups[4])

    return f"{start_month:02}-{start_day:02};{end_month:02}-{end_day:02};{multiplier}"


def add_multiplier_view(c: Connection, m: Member, s: list[str]) -> str:
    out = []

    for i in s:
        split = i.split(";")

        out.append(f"{split[2]}x multiplier from {split[0]} to {split[1]}")

    return ", ".join(out)


def add_multiplier_response(c: Connection, m: Member, s: str) -> str:
    split = s.split(";")

    return f"Added {split[2]}x multiplier from {split[0]} to {split[1]}."


def remove_multiplier_response(c: Connection, m: Member, s: str) -> str:
    split = s.split(";")

    return f"Removed {split[2]}x multiplier from {split[0]} to {split[1]}."


setting_xp_per_message = ServerSetting(
    name="Leveling XP per message",
    normal_validator=setting_is_number,
    normal_view=setting_simple_string("%s XP per message"),
    normal_response=setting_simple_string("Set the XP per message to %s"),
    default="3",
)
setting_level_up_message = ServerSetting(
    name="Leveling enable level-up message",
    normal_validator=setting_is_boolean,
    normal_transformer=setting_to_boolean,
    normal_view=setting_simple_string_boolean(
        "Level-up messages are %s", "enabled", "disabled"
    ),
    normal_response=setting_simple_string_boolean(
        "Level-up messages were %s", "enabled", "disabled"
    ),
    default="true",
)
setting_xp_per_level = ServerSetting(
    name="Leveling XP per level",
    normal_validator=setting_is_number,
    normal_view=setting_simple_string("%s XP required per level"),
    normal_response=setting_simple_string("Set XP required per level to %s"),
    default="500",
)
setting_leveling_rewards = ServerSetting(
    name="Leveling rewards",
    setting_type=SettingType.LIST,
    list_add_validator=add_reward_validator,
    list_add_transformer=add_reward_transformer,
    list_add_response=add_reward_response,
    list_remove_validator=remove_reward_validator,
    list_remove_transformer=remove_reward_transformer,
    list_view=get_reward_view,
)
setting_leveling_multipliers = ServerSetting(
    name="Leveling Multipliers",
    setting_type=SettingType.LIST,
    list_add_validator=add_multiplier_validator,
    list_add_transformer=add_multiplier_transformer,
    list_remove_validator=add_multiplier_validator,
    list_remove_transformer=add_multiplier_transformer,
    list_view=add_multiplier_view,
    list_add_response=add_multiplier_response,
    list_remove_response=remove_multiplier_response,
)


def get_xp(c: Connection, uid: int, gid: int) -> int:
    result = c.execute(
        select(leveling.c.xp).where(
            (leveling.c.uid == str(uid)) & (leveling.c.gid == str(gid))
        )
    ).fetchone()

    if not result:
        return 0

    return result[0]


def get_multiplier(c: Connection, m: Member):
    multipliers = setting_leveling_multipliers.get(c, m)

    multiplier = 1

    now = datetime.now()

    for i in multipliers:
        s: list[str] = i.split(";")
        (start_month, start_day) = s[0].split("-")
        (end_month, end_day) = s[1].split("-")

        try:
            start_dt = datetime(now.year, int(start_month), int(start_day))
            end_dt = datetime(now.year, int(end_month), int(end_day))

            if start_dt > end_dt:
                end_dt = datetime(now.year + 1, int(end_month), int(end_day))

            if start_dt <= now <= end_dt:
                multiplier *= int(s[2])
        except Exception:
            # catch leap years, we validate against 2024 since it's a leap year
            pass

    return multiplier


def add_xp(c: Connection, member: Member):
    xp_per_msg = int(setting_xp_per_message.get(c, member))
    xp_per_msg *= get_multiplier(c, member)

    existing = c.execute(
        select(leveling.c.xp).where(
            (leveling.c.uid == str(member.id))
            & (leveling.c.gid == str(member.guild.id))
        )
    ).fetchone()

    if existing is None:
        c.execute(
            insert(leveling).values(
                uid=str(member.id), gid=str(member.guild.id), xp=xp_per_msg
            )
        )
        return

    c.execute(
        update(leveling)
        .where(
            (leveling.c.uid == str(member.id))
            & (leveling.c.gid == str(member.guild.id))
        )
        .values(xp=(existing[0] or 0) + xp_per_msg)
    )


def calculate_level(c: Connection, member: Member, xp: int) -> int:
    xp_per_level = int(setting_xp_per_level.get(c, member))
    return (xp // xp_per_level) + 1


def xp_to_next_level(c: Connection, member: Member, xp: int) -> int:
    xp_per_level = int(setting_xp_per_level.get(c, member))
    return xp - ((calculate_level(c, member, xp) - 1) * xp_per_level)


async def apply_leveling_rewards(c: Connection, member: discord.Member):
    if member.guild.self_role is None:
        nekona_logger.warning("TODO: unhandable error")
        return

    if not member.guild.me.guild_permissions.manage_roles:
        nekona_logger.warning(
            "TODO: warn server owner about not able to give out roles"
        )
        return

    xp = get_xp(c, member.id, member.guild.id)
    level = calculate_level(c, member, xp)

    rewards = [i.split(";") for i in setting_leveling_rewards.get(c, member)]
    rewards = [[int(i[0]), int(i[1])] for i in rewards]
    rewards = [
        (member.guild.get_role(i[0]), i[1])
        for i in rewards
        if member.guild.get_role(i[0]) is not None
    ]

    to_add = []
    to_remove = []

    for i in rewards:
        if i[0] is None:
            continue

        if level > i[1] and i[0] not in member.roles:
            if i[0] < member.guild.self_role:
                to_add.append(i[0])
            else:
                nekona_logger.warning(
                    "TODO: warn server owner about not able to give out roles"
                )
        elif level < i[1] and i[0] in member.roles:
            if i[0] < member.guild.self_role:
                to_remove.append(i[0])
            else:
                nekona_logger.warning(
                    "TODO: warn server owner about not able to give out roles"
                )

    if len(to_add) > 0:
        await member.add_roles(*to_add)
    if len(to_remove) > 0:
        await member.remove_roles(*to_remove)
