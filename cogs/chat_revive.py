from discord import Cog, Bot, Message
from discord.ext.tasks import loop

from utils.chat_revive import update_chat_revive, notifications, setting_chat_revive_role, setting_chat_revive_channels
from utils.docs import Docs, DocsSetting
from utils.server_settings import settings, SettingType


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

    settings.add_settings(
        setting_chat_revive_role,
        setting_chat_revive_channels
    )


def docs():
    return str(
        Docs(
            name="Chat Revive",
            description="Dead channels? With the help of Chat Revive, you can revive them after a set amount of minutes.",
            settings=[
                DocsSetting(
                    name="Chat Revive Channels",
                    description="List of channels that should be in the chat revive.",
                    add_description="Syntax: \"channel, minutes\". Channel can be a mention, ID or name. Minutes is amount of minutes before a chat revive triggers.",
                    remove_description="Channel ID, name or mention to remove.",
                    setting_type=SettingType.LIST
                ),
                DocsSetting(
                    name="Chat Revive Role",
                    description="Role to ping when chat revive triggers.",
                    setting_type=SettingType.NORMAL
                )
            ]
        )
    )
