from utils.server_settings import ServerSetting, SettingType, setting_to_text_channel, setting_simple_string

setting_bot_channel = ServerSetting(
    name="Bot Channel",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_text_channel,
    normal_response=setting_simple_string(
        "The bot channel is now set to <#%s>, everything will be posted there from now on!"),
    normal_view=setting_simple_string("Bot channel: <#%s>")
)
