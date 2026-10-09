from discord import ApplicationContext, Member
from sqlalchemy import Connection, select

from database import moderator_roles


def is_user_moderator(c: Connection, m: Member):
    moderators = c.execute(
        select(moderator_roles.c.rid).where(moderator_roles.c.gid == str(m.guild.id))
    ).fetchall()
    for i in moderators:
        for j in m.roles:
            if int(i[0]) == j.id:
                return True

    return False


async def perform_basic_checks(
    c: Connection, ctx: ApplicationContext, user: Member, k: str
) -> tuple[bool, str]:
    if not is_user_moderator(c, ctx.user):
        return False, "You must be moderator in order to use this command"

    # Check if user's role is under ours
    if user.top_role > ctx.user.top_role:
        return False, f"This user has a higher rank than you, can't {k}"

    return True, ""
