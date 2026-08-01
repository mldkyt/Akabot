from utils.server_settings import ServerSetting, SettingType

setting_bot_channel = ServerSetting(
    name="Bot Channel",
    setting_type=SettingType.NORMAL,
    default=""
)

setting_admin_bot_channel = ServerSetting(
    name="Admin bot Channel",
    setting_type=SettingType.NORMAL,
    default=""
)
