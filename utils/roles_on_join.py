from discord import Forbidden, HTTPException, Member

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
                akabot_logger.warning(
                    f"Failed to fetch role {role_id} on join for {member} in guild {member.guild.id}"
                )

        try:
            await member.add_roles(*roles)
        except Forbidden:
            akabot_logger.warning(
                f"Forbidden to add roles on join for {member} in guild {member.guild.id}"
            )
        except Exception as e:
            akabot_logger.exception(f"Failed to apply roles on join for {member}: {e}")
