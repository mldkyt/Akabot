from discord import Cog, Bot, Message
from discord.ext.tasks import loop

from utils.chat_revive import update_chat_revive, notifications


class ChatRevive(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.was_started = False

    @Cog.listener()
    async def on_ready(self):
        if not self.was_started:
            self.was_started = True
            self.handle_chat_revive.start()

    @Cog.listener()
    async def on_message(self, message: Message):
        await update_chat_revive(message)

    @loop(minutes=1)
    async def handle_chat_revive(self):
        await notifications(self.bot)


def setup(bot: Bot):
    bot.add_cog(ChatRevive(bot))
