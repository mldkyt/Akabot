from datetime import datetime

from discord import Cog, Message, Bot
from discord.ext.tasks import loop

from database import engine
from logger import nekona_logger
from utils.chat_summary import chat_summary, inc, summarize, chat_summary_rows, chat_summary_extra, \
    chat_summary_rows_extra, chat_summary_unique
from utils.docs import Docs, DocsSetting
from utils.server_settings import settings, SettingType


class ChatSummary(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.task_summary.start()

    @Cog.listener()
    async def on_message(self, msg: Message):
        try:
            with engine.begin() as c:
                if msg.author.bot:
                    return

                if msg.guild is None:
                    return

                if not chat_summary.is_in_list(c, msg.author, str(msg.channel.id)):
                    return

                # Count into chat summary
                inc(c, msg)
        except Exception as e:
            nekona_logger.exception(e)

    @loop(minutes=1)
    async def task_summary(self):
        now = datetime.now()

        if now.hour != 0 or now.minute != 0:
            return

        for i in self.bot.guilds:
            with engine.begin() as c:
                try:
                    await summarize(c, i)
                except Exception as e:
                    nekona_logger.exception(e)

def setup(bot: Bot):
    bot.add_cog(ChatSummary(bot))

    settings.add_settings(
        chat_summary,
        chat_summary_rows,
        chat_summary_extra,
        chat_summary_rows_extra,
        chat_summary_unique
    )

def docs():
    return str(
        Docs(
            name="Chat Summary",
            description="Chat Summary shows a summary of who sent how many messages at the end of the day.",
            settings=[
                DocsSetting(
                    name="Chat summary channels",
                    setting_type=SettingType.LIST,
                    description="List of channels to include in the Chat Summary counting."
                ),
                DocsSetting(
                    name="Chat summary rows",
                    setting_type=SettingType.NORMAL,
                    description="The amount of rows to show in the final Chat Summary message."
                ),
                DocsSetting(
                    name="Chat summary extra summaries",
                    setting_type=SettingType.NORMAL,
                    description="Enables monthly and yearly Chat Summaries. At every end of month and year, the bot will summarize the entire month/year instead of the day."
                ),
                DocsSetting(
                    name="Chat summary rows (yearly, monthly)",
                    setting_type=SettingType.NORMAL,
                    description="The amount of rows to show in the final monthly/yearly Chat Summary message."
                ),
                DocsSetting(
                    name="Chat summary unique mode",
                    setting_type=SettingType.NORMAL,
                    description="Don't count messages sent consecutively by one member, only count conversations. For instance, the bot will count 5 messages sent right after each other by one members as 1 message."
                )
            ]
        )
    )
