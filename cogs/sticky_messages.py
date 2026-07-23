from discord import Bot, Cog, Message

from utils.sticky_message import update_sticky_message


class StickyMessages(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        await update_sticky_message(message)


def setup(bot: Bot):
    bot.add_cog(StickyMessages(bot))
