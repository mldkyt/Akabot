import datetime

from discord import Bot
from sqlalchemy import select, func, delete

from database import engine, temporary_actions


async def get_tasks_to_run():
    with engine.begin() as c:
        tasks_to_run = c.execute(
            select(temporary_actions.c.action, temporary_actions.c.gid, temporary_actions.c.uid, temporary_actions.c.arg)
            .where(temporary_actions.c.runs_at <= func.now())
        ).fetchall()
    return tasks_to_run


async def mark_task_handled(gid, uid):
    with engine.begin() as c:
        c.execute(
            delete(temporary_actions)
            .where((temporary_actions.c.gid == gid) & (temporary_actions.c.uid == uid))
        )


async def _handle_unban(bot: Bot, gid, uid):
    guild = bot.get_guild(int(gid))
    if guild is None:
        return

    if not guild.me.guild_permissions.ban_members:
        return

    await guild.unban(uid)


async def _handle_remove_role(bot: Bot, gid, uid, role_id):
    guild = bot.get_guild(int(gid))
    if guild is None:
        return

    if not guild.me.guild_permissions.manage_roles:
        return

    member = guild.get_member(int(uid))
    if member is None:
        return

    role = guild.get_role(int(role_id))
    if role is None:
        return

    await member.remove_roles(role)


async def handle_task(bot: Bot, action, gid, uid, arg):
    if action == "remove_role":
        await _handle_remove_role(bot, gid, uid, arg)

    elif action == "unban":
        await _handle_unban(bot, gid, uid)

    else:
        raise ValueError("action")


async def add_temporary_action(gid: int, action: str, uid: int, duration: datetime.timedelta, arg: str | None=None):
    with engine.begin() as c:
        c.execute(
            temporary_actions.insert().values(
                gid=gid,
                uid=uid,
                action=action,
                arg=arg,
                runs_at=datetime.datetime.now() + duration
            )
        )
