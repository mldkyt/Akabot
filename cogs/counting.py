import os

from discord import Bot, Cog, Message

from database import engine
from utils.counting import (
    handle_counting_channel,
    setting_counting_channels,
)

MESSAGE_INTENT = os.getenv("MESSAGE_INTENT", "0") == "1"


class Counting(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot:
            return
        if message.guild is None:
            return

        with engine.begin() as c:
            if not setting_counting_channels.is_in_list(
                c, message.guild.id, str(message.channel.id)
            ):
                return

            await handle_counting_channel(c, message)


def setup(bot: Bot):
    if not MESSAGE_INTENT:
        return

    bot.add_cog(Counting(bot))
