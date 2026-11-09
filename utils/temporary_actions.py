import datetime

from discord import Bot, Object
from sqlalchemy import select, func, delete, update

from database import engine, temporary_actions

# Give up on a task after this many failed attempts so a permanently broken
# action (e.g. the bot was removed from the guild) does not retry forever.
MAX_ATTEMPTS = 10


async def get_tasks_to_run():
    with engine.begin() as c:
        tasks_to_run = c.execute(
            select(
                temporary_actions.c.id,
                temporary_actions.c.action,
                temporary_actions.c.gid,
                temporary_actions.c.uid,
                temporary_actions.c.arg,
                temporary_actions.c.attempts,
            )
            .where(temporary_actions.c.runs_at <= func.now())
        ).fetchall()
    return tasks_to_run


async def mark_task_handled(task_id):
    with engine.begin() as c:
        c.execute(
            delete(temporary_actions)
            .where(temporary_actions.c.id == task_id)
        )


async def mark_task_failed(task_id):
    with engine.begin() as c:
        c.execute(
            update(temporary_actions)
            .where(temporary_actions.c.id == task_id)
            .values(attempts=temporary_actions.c.attempts + 1)
        )


async def _handle_unban(bot: Bot, gid, uid):
    guild = bot.get_guild(int(gid))
    if guild is None:
        raise RuntimeError(f"Guild {gid} is not available")

    if guild.me is None or not guild.me.guild_permissions.ban_members:
        raise RuntimeError(f"Missing ban permission in guild {gid}")

    await guild.unban(Object(id=int(uid)))


async def _handle_remove_role(bot: Bot, gid, uid, role_id):
    guild = bot.get_guild(int(gid))
    if guild is None:
        raise RuntimeError(f"Guild {gid} is not available")

    if guild.me is None or not guild.me.guild_permissions.manage_roles:
        raise RuntimeError(f"Missing manage roles permission in guild {gid}")

    member = guild.get_member(int(uid))
    if member is None:
        # The member left the guild, so there is no role left to remove.
        return

    role = guild.get_role(int(role_id))
    if role is None:
        # The role was deleted, so there is nothing left to remove.
        return

    await member.remove_roles(role)


async def handle_task(bot: Bot, action, gid, uid, arg):
    if action == "remove_role":
        await _handle_remove_role(bot, gid, uid, arg)

    elif action == "unban":
        await _handle_unban(bot, gid, uid)

    else:
        raise ValueError(f"Unknown temporary action: {action}")


async def add_temporary_action(gid: int, action: str, uid: int, duration: datetime.timedelta, arg: str | None=None):
    with engine.begin() as c:
        c.execute(
            temporary_actions.insert().values(
                gid=str(gid),
                uid=str(uid),
                action=action,
                arg=arg,
                runs_at=datetime.datetime.now(datetime.UTC) + duration
            )
        )
