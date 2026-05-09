from discord import Member
from sqlalchemy import Connection

from utils.server_settings import ServerSetting, SettingType, setting_to_role, setting_simple_string


def verify_mode(c: Connection, m: Member, value: str) -> tuple[bool, str]:
    if value in ["none", "math", "silly"]:
        return True, value

    return False, "This value is invalid, the valid values are \"none\", \"math\", \"silly\""


setting_verification_role = ServerSetting(
    name="Verification role",
    description="The verification role",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_role,
    normal_response=setting_simple_string("Verification role was set to <@&%s>"),
    normal_view=setting_simple_string("Verification role: <@&%s>"),
)

setting_verification_mode = ServerSetting(
    name="Verification mode",
    description="The verification mode",
    setting_type=SettingType.NORMAL,
    normal_processor=verify_mode,
    normal_response=setting_simple_string("Verification mode was set to %s"),
    normal_view=setting_simple_string("Verification mode: %s"),
    default="none"
)
