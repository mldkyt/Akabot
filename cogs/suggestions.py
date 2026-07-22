from discord import Bot, Cog, Message

from logger import akabot_logger
from utils.suggestions import VotingOptions, handle_suggestion_message


class Suggestions(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(VotingOptions())

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot or message.guild is None:
            return

        await handle_suggestion_message(message)


def setup(bot: Bot):
    if not bot.intents.message_content:
        akabot_logger.warning(
            "Suggestions module not supported if there's no message intent"
        )
        return

    return bot.add_cog(Suggestions(bot))
