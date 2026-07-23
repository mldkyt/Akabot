import datetime

from discord import Member

from database import engine
from utils.server_settings import ServerSetting, SettingType

setting_no_avatar = ServerSetting(
    name="Kick users with no avatar", setting_type=SettingType.NORMAL, default="false"
)

setting_minimum_age = ServerSetting(
    name="Minimum user age (days)", setting_type=SettingType.NORMAL, default="false"
)


async def verify_member(member: Member):
    with engine.begin() as c:
        kick_no_avatar = setting_no_avatar.get(c, member.guild.id) == "true"
        kick_minimum_age = int(setting_minimum_age.get(c, member.guild.id))

    if kick_no_avatar and member.avatar is None:
        await member.kick(reason="Anti Raid: User has no avatar")
        return

    if kick_minimum_age == 0:
        return

    account_age = (
        datetime.datetime.now() - member.created_at.replace(tzinfo=None)
    ).days
    if account_age < kick_minimum_age:
        await member.kick(
            reason=f"Anti Raid: User is below minimum account age ({account_age} < {kick_minimum_age})"
        )
