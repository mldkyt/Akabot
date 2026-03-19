from discord import Cog, Bot
from discord.ext.tasks import loop

from utils.docs import Docs, DocsSetting
from utils.server_settings import SettingType, settings
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


def docs():
    return str(
        Docs(
            name="Statistic Channels",
            description="You can set up channels that periodically update with the statistics of your server on the top of your server channel list. Create a voice channel and put it on top of the list, and ensure the bot has channel edit permissions.",
            settings=[
                DocsSetting(
                    name="Statistic Channels",
                    description="Set up statistic channels. Templates have {members}, {bots}, {users}, {guild} and {owner} so far. You can suggest more in the support Discord server :)",
                    add_description="Format is \"<channel mention, name or ID>;<template>\". Template is above.",
                    remove_description="Mention the channel that you want to remove.",
                    setting_type=SettingType.LIST
                )
            ]
        )
    )
