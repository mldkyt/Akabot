from datetime import datetime

from fluxer import Bot, Cog, Message

from database import engine
from logger import nekona_logger
from utils.chat_summary import (
    chat_summary,
    chat_summary_extra,
    chat_summary_rows,
    chat_summary_rows_extra,
    chat_summary_unique,
    inc,
    perform_backfill,
    summarize,
)
from utils.docs import Docs
from utils.server_settings import settings


class ChatSummary(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    has_init = False

    @Cog.listener()
    async def on_ready(self):
        if not self.has_init:
            # self.task_summary.start()

            # TODO: missing channels properties on guilds
            # try:
            #     with engine.begin() as c:
            #         for i in self.bot.guilds:
            #             for j in chat_summary.get_guild(c, i):
            #                 channel = await i.fetch_channel(int(j))
            #                 if not isinstance(channel, TextChannel):
            #                     continue

            #                 nekona_logger.debug("[Chat Summary/Backfill] Backfilling channel %s", channel.name)
            #                 await perform_backfill(i, channel)
            #                 nekona_logger.debug("[Chat Summary/Backfill] Backfilling channel %s finished", channel.name)
            # except Exception:
            #     nekona_logger.exception("Error when backfilling channels on startup")

            self.has_init = True

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

    # @loop(minutes=1)
    # async def task_summary(self):
    #     now = datetime.now()

    #     if now.hour != 0 or now.minute != 0:
    #         return

    #     for i in self.bot.guilds:
    #         try:
    #             with engine.begin() as c:
    #                 await summarize(c, i)
    #         except Exception:
    #             nekona_logger.exception("Error during summarizing")

    # @Cog.command()
    # async def backfill(self, ctx: ApplicationContext):
    #     """Backfill a Chat Summary channel back to the start of the year"""
    #     if not isinstance(ctx.channel, TextChannel):
    #         await ctx.respond(
    #             "This command is only applicable inside of a text channel",
    #             ephemeral=True,
    #         )
    #         return

    #     status = await ctx.respond("Backfilling channel...")
    #     await perform_backfill(ctx.guild, ctx.channel)
    #     await status.message.edit(content="Backfilling complete!")
    #     await status.message.delete(delay=5)


def setup(bot: Bot):
    bot.add_cog(ChatSummary(bot))

    settings.add_settings(
        chat_summary,
        chat_summary_rows,
        chat_summary_extra,
        chat_summary_rows_extra,
        chat_summary_unique,
    )


def docs():
    return str(
        Docs(
            name="Chat Summary",
            description="Chat Summary shows a summary of who sent how many messages at the end of the day.",
            settings=[
                chat_summary,
                chat_summary_rows,
                chat_summary_extra,
                chat_summary_rows_extra,
                chat_summary_unique,
            ],
        )
    )
