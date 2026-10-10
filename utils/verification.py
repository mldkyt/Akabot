import datetime

from discord import Guild

from database import engine
from utils.server_settings import KV


setting_verification_role = KV(
    name="Verification role",
)

setting_verification_mode = KV(
    name="Verification mode",
    default="none"
)

setting_introduction_channel = KV(
    name="Introduction channel",
    default=""
)

setting_kick_unverified_users = KV(
    name="Kick unverified users",
    default="false"
)

async def unverified_members(guild: Guild):
    with engine.begin() as c:
        verified_role_id = setting_verification_role.get(c, guild.id)

    if not verified_role_id or not str(verified_role_id).isnumeric():
        # No verification role configured, so nobody can be known to be
        # verified. Yield nothing rather than kicking the whole guild.
        return

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

