import asyncio
from datetime import date, datetime

from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Message,
    SlashCommandGroup,
    TextChannel,
)
from discord.ext.tasks import loop

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
    perform_backfill_feedback,
    summarize,
)
from utils.docs import Docs, DocsSetting
from utils.server_settings import SettingType, settings


class ChatSummary(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.task_summary.start()

        try:
            with engine.begin() as c:
                async for i in self.bot.fetch_guilds(limit=None):
                    for j in chat_summary.get_direct(c, i):
                        channel = await i.fetch_channel(int(j))
                        if not isinstance(channel, TextChannel):
                            continue

                        async for m in perform_backfill(i, channel):
                            nekona_logger.info("Backfill info: %s", m)
        except Exception:
            nekona_logger.exception("Error when backfilling channels on startup")

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
            try:
                with engine.begin() as c:
                    await summarize(c, i)
            except Exception as e:
                nekona_logger.exception("Error during summarizing")

    chat_summary_commands = SlashCommandGroup(name="chat_summary")

    @chat_summary_commands.command()
    async def backfill(self, ctx: ApplicationContext):
        """Backfill a Chat Summary channel back to the start of the year"""
        if not isinstance(ctx.channel, TextChannel):
            await ctx.respond(
                "This command is only applicable inside of a text channel",
                ephemeral=True,
            )
            return

        await perform_backfill_feedback(ctx)


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
                DocsSetting(
                    name="Chat summary channels",
                    setting_type=SettingType.LIST,
                    description="List of channels to include in the Chat Summary counting.",
                ),
                DocsSetting(
                    name="Chat summary rows",
                    setting_type=SettingType.NORMAL,
                    description="The amount of rows to show in the final Chat Summary message.",
                ),
                DocsSetting(
                    name="Chat summary extra summaries",
                    setting_type=SettingType.NORMAL,
                    description="Enables monthly and yearly Chat Summaries. At every end of month and year, the bot will summarize the entire month/year instead of the day.",
                ),
                DocsSetting(
                    name="Chat summary rows (yearly, monthly)",
                    setting_type=SettingType.NORMAL,
                    description="The amount of rows to show in the final monthly/yearly Chat Summary message.",
                ),
                DocsSetting(
                    name="Chat summary unique mode",
                    setting_type=SettingType.NORMAL,
                    description="Don't count messages sent consecutively by one member, only count conversations. For instance, the bot will count 5 messages sent right after each other by one members as 1 message.",
                ),
            ],
        )
    )
