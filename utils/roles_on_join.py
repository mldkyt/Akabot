from discord import Member, Forbidden, HTTPException

from database import engine
from logger import akabot_logger
from utils.server_settings import ServerSetting, setting_to_role, SettingType, setting_simple_string, \
    setting_simple_list_string_item

setting_roles_on_join = ServerSetting(
    name="Roles on join",
    description="The roles to be added to members on join",
    list_add_processor=setting_to_role,
    list_remove_processor=setting_to_role,
    setting_type=SettingType.LIST,
    list_add_response=setting_simple_string("Added <@&%s> to roles on join"),
    list_remove_response=setting_simple_string("Removed <@&%s> from roles on join"),
    list_view=setting_simple_list_string_item("Roles on join: %s", ", ", "None", "<@&%s>"),
)


async def apply_roles(member: Member):
    with engine.begin() as c:
        roles_ids = setting_roles_on_join.get(c, member)
        roles = []

        for role_id in roles_ids:
            try:
                role = await member.guild.fetch_role(int(role_id))
                roles.append(role)
            except HTTPException:
                pass

        akabot_logger.debug("Adding %d roles on join to %s", len(roles), member.display_name)

        try:
            await member.add_roles(*roles)
        except Forbidden:
            pass
        except Exception:
            akabot_logger.exception("An error occured when applying roles for %s:", member.display_name)
