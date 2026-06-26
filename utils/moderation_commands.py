from discord import ApplicationContext, Member
from sqlalchemy import Connection

from utils.server_settings import (
    ServerSetting,
    SettingType,
)

moderator_roles = ServerSetting(
    name="Moderator roles",
    setting_type=SettingType.LIST,
)


def is_user_moderator(c: Connection, m: Member):
    moderators = moderator_roles.get(c, m.guild.id)
    for i in moderators:
        for j in m.roles:
            if int(i) == j.id:
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
