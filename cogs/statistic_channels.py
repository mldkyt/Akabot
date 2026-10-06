from discord import Cog, Bot
from discord.ext.tasks import loop

from utils.statistic_channels import update


class StatisticChannels(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        if not self.update_channels.is_running():
            self.update_channels.start()

    @loop(minutes=5)
    async def update_channels(self):
        await update(self.bot)


def setup(bot: Bot):
    bot.add_cog(StatisticChannels(bot))
