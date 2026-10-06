import datetime
from typing import Any

import discord
from discord import Member
from sqlalchemy import Connection, insert, select, update

from database import (
    leveling,
    message_counting_members,
    message_counting_rewards,
    vote_points,
)
from logger import akabot_logger
from utils.premium import has_premium
from utils.server_settings import (
    ServerSetting,
    SettingType,
)
from utils.timezones import get_now

setting_xp_per_message = ServerSetting(
    name="Leveling XP per message",
    default="3",
)
setting_level_up_message = ServerSetting(
    name="Leveling enable level-up message",
    default="true",
)
setting_level_up_message_text = ServerSetting(
    name="Leveling level-up message content",
    default="**You leveled up!** {old} -> {new}",
)
setting_xp_per_level = ServerSetting(
    name="Leveling XP per level",
    default="500",
)
setting_leveling_rewards = ServerSetting(
    name="Leveling rewards",
    setting_type=SettingType.LIST,
)
setting_leveling_multipliers = ServerSetting(
    name="Leveling Multipliers",
    setting_type=SettingType.LIST,
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
    multipliers = setting_leveling_multipliers.get(c, m.guild.id)

    multiplier = 1

    now = get_now(m.guild.id, c)

    for i in multipliers:
        s: list[str] = i.split(";")
        (start_month, start_day) = s[0].split("-")
        (end_month, end_day) = s[1].split("-")

        try:
            start_dt = datetime.datetime(now.year, int(start_month), int(start_day))
            end_dt = datetime.datetime(now.year, int(end_month), int(end_day))

            if start_dt > end_dt:
                end_dt = datetime.datetime(now.year + 1, int(end_month), int(end_day))

            if start_dt <= now <= end_dt:
                multiplier *= int(s[2])
        except Exception:
            # catch leap years, we validate against 2024 since it's a leap year
            akabot_logger.warning(
                f"Failed to parse xp multiplier date {start_month}/{start_day} - {end_month}/{end_day} for member {m}"
            )

    # Multipliers from message counting
    message_count = c.execute(
        select(message_counting_members.c.messages).where(
            (message_counting_members.c.uid == str(m.id))
            & (message_counting_members.c.gid == str(m.guild.id))
        )
    ).fetchone()

    if message_count:
        message_count_multipliers = c.execute(
            select(message_counting_rewards.c.multiplier).where(
                (message_counting_rewards.c.gid == str(m.guild.id))
                & (message_counting_rewards.c.type == "multiplier")
            )
        ).fetchall()

        for reward in message_count_multipliers:
            multiplier += reward[0]

    # Voting multiplier
    voting = c.execute(
        select(vote_points.c.last_vote).where(vote_points.c.uid == str(m.id))
    ).fetchone()
    if voting is not None and voting[0] is not None:
        now = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        last_vote: datetime.datetime = voting[0]
        if (now - last_vote).total_seconds() < 12 * 3600:
            multiplier *= 2

    return multiplier


def add_xp(c: Connection, member: Member):
    xp_per_msg = int(setting_xp_per_message.get(c, member.guild.id))
    xp_per_msg *= get_multiplier(c, member)
    xp_per_msg = int(xp_per_msg)

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


def edit_xp(c: Connection, member: Member, xp: int, existing: Any | None = None):
    """SET xp to a level"""

    if existing is None:
        existing = c.execute(
            select(leveling.c.xp).where(
                (leveling.c.uid == str(member.id))
                & (leveling.c.gid == str(member.guild.id))
            )
        ).fetchone()

    if existing is None:
        c.execute(
            insert(leveling).values(uid=str(member.id), gid=str(member.guild.id), xp=xp)
        )
        return

    c.execute(
        update(leveling)
        .where(
            (leveling.c.uid == str(member.id))
            & (leveling.c.gid == str(member.guild.id))
        )
        .values(xp=xp)
    )


def edit_xp_rel(c: Connection, member: Member, xp: int):
    """ADD or REMOVE xp from a member"""
    existing = c.execute(
        select(leveling.c.xp).where(
            (leveling.c.uid == str(member.id))
            & (leveling.c.gid == str(member.guild.id))
        )
    ).fetchone()

    if existing is not None and existing[0] + xp < 0:
        print(
            "existing XP is",
            existing[0],
            "XP is",
            xp,
            "subtraction is",
            existing[0] + xp,
        )
        return False, "Unable to set XP to a negative number"

    edit_xp(
        c, member, (existing[0] if existing is not None else 0) + xp, existing=existing
    )
    return True, None


def calculate_level(c: Connection, member: Member, xp: int) -> int:
    xp_per_level = int(setting_xp_per_level.get(c, member.guild.id))
    level = (xp // xp_per_level) + 1
    if has_premium(c, member.guild.id):
        return level
    return min(level, 50)


def xp_to_next_level(c: Connection, member: Member, xp: int) -> int:
    xp_per_level = int(setting_xp_per_level.get(c, member.guild.id))
    return xp - ((calculate_level(c, member, xp) - 1) * xp_per_level)


async def apply_leveling_rewards(c: Connection, member: discord.Member):
    if member.guild.self_role is None:
        akabot_logger.warning("TODO: unhandable error")
        return

    if not member.guild.me.guild_permissions.manage_roles:
        akabot_logger.warning(
            "TODO: warn server owner about not able to give out roles"
        )
        return

    xp = get_xp(c, member.id, member.guild.id)
    level = calculate_level(c, member, xp)

    rewards = [i.split(";") for i in setting_leveling_rewards.get(c, member.guild.id)]
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

        if level >= i[1] and i[0] not in member.roles:
            if i[0] < member.guild.self_role:
                to_add.append(i[0])
            else:
                akabot_logger.warning(
                    "TODO: warn server owner about not able to give out roles"
                )
        elif level < i[1] and i[0] in member.roles:
            if i[0] < member.guild.self_role:
                to_remove.append(i[0])
            else:
                akabot_logger.warning(
                    "TODO: warn server owner about not able to give out roles"
                )

    if len(to_add) > 0:
        await member.add_roles(*to_add)
    if len(to_remove) > 0:
        await member.remove_roles(*to_remove)
