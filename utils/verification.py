from utils.server_settings import ServerSetting, SettingType, setting_to_role, setting_simple_string

setting_verification_role = ServerSetting(
    name="Verification role",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_role,
    normal_response=setting_simple_string("Verification role was set to <@&%s>"),
    normal_view=setting_simple_string("Verification role: <@&%s>"),
)
