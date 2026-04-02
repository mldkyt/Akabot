from discord import Cog, Bot, Message

from utils.docs import Docs, DocsSetting
from utils.meow_back import meow_back_for_message, meowing, wafing, barking, colon_3, owo, awawa
from utils.server_settings import settings, SettingType


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


def docs():
    return str(
        Docs(
            name="Meowing Back :3",
            description="This is a silly module (disabled by default) for cat friends, dog friends, fox friends, and any other friends, which makes the bot meow, bark, waf, awawa, owo or :3 back at users. It's purely silly :3",
            settings=[
                DocsSetting(
                    name="Meow back at messages",
                    description="Meow back at messages. :3",
                    setting_type=SettingType.NORMAL,
                    set_description="Enables or disables meowing at messages. :3",
                ),
                DocsSetting(
                    name="Waf back at messages",
                    description="Waf back at messages. :3",
                    setting_type=SettingType.NORMAL,
                    set_description="Enables or disables waffing at messages. :3",
                ),
                DocsSetting(
                    name="Bark back at messages",
                    description="Bark back at messages. :3",
                    setting_type=SettingType.NORMAL,
                    set_description="Enables or disables barking at messages. :3",
                ),
                DocsSetting(
                    name=":3 back at messages",
                    description=":3 back at messages. :3",
                    setting_type=SettingType.NORMAL,
                    set_description="Enables or disables :3ing at messages. :3",
                ),
                DocsSetting(
                    name="OwO back at messages",
                    description="OwO back at messages. :3",
                    setting_type=SettingType.NORMAL,
                    set_description="Enables or disables OwOing at messages. :3",
                ),
                DocsSetting(
                    name="awawa back at messages",
                    description="awawa back at messages. :3",
                    setting_type=SettingType.NORMAL,
                    set_description="Enables or disables awawaing at messages. :3",
                ),
            ]
        )
    )
