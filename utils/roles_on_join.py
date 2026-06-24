from discord import Member, Forbidden, HTTPException

from database import engine
from logger import akabot_logger
from utils.server_settings import ServerSetting, SettingType

setting_roles_on_join = ServerSetting(
    name="Roles on join",
    setting_type=SettingType.LIST,
)


async def apply_roles(member: Member):
    with engine.begin() as c:
        roles_ids = setting_roles_on_join.get(c, member.guild.id)
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
