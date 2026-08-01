from discord import Member
from sqlalchemy import Connection

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

introduction_channel = ServerSetting(
    name="Introduction channel",
    setting_type=SettingType.NORMAL,
    default=""
)
