from datetime import datetime

from discord import Cog, Message, Bot
from discord.ext.tasks import loop

from database import engine
from utils.chat_summary import chat_summary, inc, summarize, chat_summary_rows, chat_summary_extra, \
    chat_summary_rows_extra, chat_summary_unique
from utils.server_settings import settings


class ChatSummary(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.task_summary.start()

    @Cog.listener()
    async def on_message(self, msg: Message):
        with engine.begin() as c:
            if msg.author.bot:
                return

            if msg.guild is None:
                return

            if not chat_summary.is_in_list(c, msg.author, str(msg.channel.id)):
                return

            # Count into chat summary
            inc(c, msg)

    @loop(minutes=1)
    async def task_summary(self):
        now = datetime.now()

        if now.hour != 0 or now.minute != 0:
            return

        for i in self.bot.guilds:
            with engine.begin() as c:
                await summarize(c, i)

def setup(bot: Bot):
    bot.add_cog(ChatSummary(bot))

    settings.add_settings(
        chat_summary,
        chat_summary_rows,
        chat_summary_extra,
        chat_summary_rows_extra,
        chat_summary_unique
    )
