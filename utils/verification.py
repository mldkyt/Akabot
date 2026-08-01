import datetime

from discord import Guild

from database import engine
from utils.server_settings import ServerSetting, SettingType


setting_verification_role = ServerSetting(
    name="Verification role",
    setting_type=SettingType.NORMAL,
)

setting_verification_mode = ServerSetting(
    name="Verification mode",
    setting_type=SettingType.NORMAL,
    default="none"
)

setting_introduction_channel = ServerSetting(
    name="Introduction channel",
    setting_type=SettingType.NORMAL,
    default=""
)

setting_kick_unverified_users = ServerSetting(
    name="Kick unverified users",
    setting_type=SettingType.NORMAL,
    default="false"
)

async def unverified_members(guild: Guild):
    with engine.begin() as c:
        verified_role_id = setting_verification_role.get(c, guild.id)

    member_role = await guild.fetch_role(int(verified_role_id))
    async for member in guild.fetch_members(limit=None):
        if member.bot:
            continue
        if member.guild_permissions.manage_guild or member.guild_permissions.kick_members or member.guild_permissions.ban_members or member.guild_permissions.mute_members:
            continue
        if member_role in member.roles:
            continue
        if member.joined_at is not None and (datetime.datetime.now(datetime.UTC) - member.joined_at) < datetime.timedelta(days=1):
            continue

        yield member

