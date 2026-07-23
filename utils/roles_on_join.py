import sentry_sdk
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
                pass

        try:
            await member.add_roles(*roles)
        except Forbidden:
            pass
        except Exception as e:
            sentry_sdk.capture_exception(e)
