from discord import Cog, Bot
from discord.ext.tasks import loop

from utils.docs import Docs
from utils.server_settings import settings
from utils.statistic_channels import update, setting_statistic_channels


class StatisticChannels(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.update_channels.start()

    @loop(minutes=5)
    async def update_channels(self):
        await update(self.bot)


def setup(bot: Bot):
    bot.add_cog(StatisticChannels(bot))

    settings.add_setting(
        setting_statistic_channels
    )
