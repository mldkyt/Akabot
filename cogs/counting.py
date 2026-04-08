import os

from discord import Bot, Cog, Message

from database import engine
from utils.counting import (
    any_count_mode,
    any_count_mode_count_frequency,
    any_count_mode_count_words,
    any_count_mode_minimum_frequency,
    handle_counting_channel,
    same_member_counting_mode,
    setting_counting_channels,
)
from utils.docs import Docs
from utils.server_settings import settings

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
                c, message.author, str(message.channel.id)
            ):
                return

            await handle_counting_channel(c, message)


def setup(bot: Bot):
    if not MESSAGE_INTENT:
        return

    bot.add_cog(Counting(bot))

    settings.add_settings(
        setting_counting_channels,
        any_count_mode,
        any_count_mode_count_words,
        any_count_mode_count_frequency,
        any_count_mode_minimum_frequency,
        same_member_counting_mode,
    )


def docs():
    return str(
        Docs(
            name="Counting",
            description="Counting channels add a bit of fun into your server with channels purely for counting.",
            settings=[
                setting_counting_channels,
                any_count_mode,
                any_count_mode_count_words,
                any_count_mode_count_frequency,
                any_count_mode_minimum_frequency,
                same_member_counting_mode
            ],
        )
    )
