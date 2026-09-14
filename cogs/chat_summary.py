from datetime import datetime

import sentry_sdk
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
from logger import akabot_logger
from utils.chat_summary import (
    SummaryHistoryView,
    chat_summary,
    inc,
    perform_backfill,
    summarize,
)


class ChatSummary(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    has_init = False

    @Cog.listener()
    async def on_ready(self):
        if not self.has_init:
            self.task_summary.start()

            try:
                self.bot.add_view(SummaryHistoryView())

                with engine.begin() as c:
                    async for i in self.bot.fetch_guilds(limit=None):
                        for j in chat_summary.get(c, i.id):
                            channel = await i.fetch_channel(int(j))
                            if not isinstance(channel, TextChannel):
                                continue

                            await perform_backfill(i, channel)
            except Exception as e:
                akabot_logger.exception(f"Failed to initialize chat summary backfill: {e}")
                sentry_sdk.capture_exception(e)

            self.has_init = True

    @Cog.listener()
    async def on_message(self, msg: Message):
        try:
            with engine.begin() as c:
                if msg.author.bot:
                    return

                if msg.guild is None:
                    return

                if not chat_summary.is_in_list(c, msg.guild.id, str(msg.channel.id)):
                    return

                # Count into chat summary
                inc(c, msg)
        except Exception as e:
            akabot_logger.exception(f"Failed to process chat summary message {msg.id}: {e}")
            sentry_sdk.capture_exception(e)

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
                akabot_logger.exception(f"Failed to summarize chat for guild {i.id}: {e}")
                sentry_sdk.capture_exception(e)

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

        with engine.begin() as c:
            if not chat_summary.is_in_list(c, ctx.guild.id, str(ctx.channel.id)):
                await ctx.respond(
                    "This channel is not a chat summary channel", ephemeral=True
                )
                return

        status = await ctx.respond("Backfilling channel...")
        await perform_backfill(ctx.guild, ctx.channel)
        await status.message.edit(content="Backfilling complete!")
        await status.message.delete(delay=5)


def setup(bot: Bot):
    bot.add_cog(ChatSummary(bot))
