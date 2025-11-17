import os

from discord import Cog, Bot, Message

from database import engine
from utils.counting import setting_counting_channels, handle_counting_channel, any_count_mode, \
    any_count_mode_count_words, any_count_mode_count_frequency, any_count_mode_minimum_frequency, \
    same_member_counting_mode
from utils.docs import Docs, DocsSetting
from utils.server_settings import settings, SettingType

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
            if not setting_counting_channels.is_in_list(c, message.author, str(message.channel.id)):
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
        same_member_counting_mode
    )

def docs():
    return str(
        Docs(
            name="Counting",
            description="Counting channels add a bit of fun into your server with channels purely for counting.",
            settings=[
                DocsSetting(
                    name="Counting channels",
                    setting_type=SettingType.LIST,
                    description="The list of channels that should be considered \"counting channels\". Any channels in this list will be marked as counting channels."
                ),
                DocsSetting(
                    name="Counting same member mode",
                    setting_type=SettingType.NORMAL,
                    description="Determines if a member can count twice consecutively or not. If set to \"no\", it will let anyone count as many times as they wish."
                ),
                DocsSetting(
                    name="Counting any count mode",
                    setting_type=SettingType.NORMAL,
                    description="Instead of explicitly checking for numbers, check for numbers in the entire message instead. Allows members to add anything to the message."
                ),
                DocsSetting(
                    name="Counting any count mode: Count frequency of words",
                    setting_type=SettingType.NORMAL,
                    description="If any count mode is enabled, a number is also how many times has one word appeared in the counting message."
                ),
                DocsSetting(
                    name="Counting any count mode: Count total word count",
                    setting_type=SettingType.NORMAL,
                    description="If any count mode is enabled, a number is also how many words are in the message."
                ),
                DocsSetting(
                    name="Counting any count mode: Minimum frequency",
                    setting_type=SettingType.NORMAL,
                    description="If any count mode: count frequency of words is enabled, this is the minimum amount of that word has to be in the message to be considered as a number."
                )
            ]
        )
    )
