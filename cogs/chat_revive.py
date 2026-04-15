from fluxer import Bot, Cog, Message

from utils.chat_revive import (
    setting_chat_revive_channels,
    setting_chat_revive_role,
    update_chat_revive,
)
from utils.docs import Docs
from utils.server_settings import settings


class ChatRevive(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.was_started = False

    @Cog.listener()
    async def on_ready(self):
        if not self.was_started:
            self.was_started = True
            # self.handle_chat_revive.start()

    @Cog.listener()
    async def on_message(self, message: Message):
        await update_chat_revive(message)

    # @loop(minutes=1)
    # async def handle_chat_revive(self):
    #     await notifications(self.bot)


async def setup(bot: Bot):
    await bot.add_cog(ChatRevive(bot))

    settings.add_settings(setting_chat_revive_role, setting_chat_revive_channels)


def docs():
    return str(
        Docs(
            name="Chat Revive",
            description="Dead channels? With the help of Chat Revive, you can revive them after a set amount of minutes.",
            settings=[setting_chat_revive_role, setting_chat_revive_channels],
        )
    )
