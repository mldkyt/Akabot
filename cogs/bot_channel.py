from fluxer import Bot

from utils.bot_channel import setting_bot_channel
from utils.server_settings import settings


async def setup(bot: Bot):
    settings.add_setting(setting_bot_channel)
