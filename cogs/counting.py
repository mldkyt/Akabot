import os

from discord import Bot, Cog, Message
from sqlalchemy import select

from database import counting_channels, engine
from utils.counting import (
    handle_counting_channel,
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
            configured = c.execute(
                select(counting_channels.c.current_count).where(
                    (counting_channels.c.gid == str(message.guild.id))
                    & (counting_channels.c.cid == str(message.channel.id))
                )
            ).fetchone()
            if configured is None:
                return

            await handle_counting_channel(c, message)


def setup(bot: Bot):
    if not MESSAGE_INTENT:
        return

    bot.add_cog(Counting(bot))
