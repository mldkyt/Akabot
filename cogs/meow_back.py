from discord import Cog, Bot, Message

from utils.docs import Docs
from utils.meow_back import meow_back_for_message, meowing, wafing, barking, colon_3, owo, awawa
from utils.server_settings import settings


class MeowBack(Cog):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return

        meows = meow_back_for_message(message)

        if len(meows.strip()) > 0:
            await message.channel.send(meows)


def setup(bot: Bot):
    bot.add_cog(MeowBack(bot))

    settings.add_settings(
        meowing,
        wafing,
        barking,
        colon_3,
        owo,
        awawa
    )
