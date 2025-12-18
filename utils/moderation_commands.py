from discord import ApplicationContext, Member
from sqlalchemy import Connection

from utils.server_settings import (
    ServerSetting,
    SettingType,
    setting_is_role,
    setting_simple_list_string_item,
    setting_simple_string,
    setting_to_role,
)

moderator_roles = ServerSetting(
    name="Moderator roles",
    setting_type=SettingType.LIST,
    list_add_validator=setting_is_role,
    list_add_transformer=setting_to_role,
    list_add_response=setting_simple_string("Added <@&%s> into moderator roles"),
    list_remove_validator=setting_is_role,
    list_remove_transformer=setting_to_role,
    list_remove_response=setting_simple_string("Removed <@&%s> from moderator roles"),
    list_view=setting_simple_list_string_item(
        "Moderator roles: %s", ", ", "None", "<@&%s>"
    ),
)


def is_user_moderator(c: Connection, m: Member):
    moderators = moderator_roles.get(c, m)
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

    # Check bot role
    if ctx.guild.me.top_role < ctx.user.top_role:
        return (
            False,
            f"That user has a higher rank than me, please give me a higher rank to {k} that user",
        )

    return True, ""
