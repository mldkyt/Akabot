from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Message,
    SlashCommandGroup,
    TextChannel,
)
from discord.ext.tasks import loop
from sqlalchemy import select

from database import chat_summary_channels, engine
from logger import akabot_logger
from utils.chat_summary import (
    SummaryHistoryView,
    inc,
    perform_backfill,
    summarize,
)
from utils.timezones import get_now


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
                        configured = c.execute(
                            select(chat_summary_channels.c.cid)
                            .where(chat_summary_channels.c.gid == str(i.id))
                            .order_by(chat_summary_channels.c.cid)
                        ).fetchall()
                        for j in configured:
                            channel = await i.fetch_channel(int(j[0]))
                            if not isinstance(channel, TextChannel):
                                continue

                            await perform_backfill(i, channel)
            except Exception as e:
                akabot_logger.exception(f"Failed to initialize chat summary backfill: {e}")

            self.has_init = True

    @Cog.listener()
    async def on_message(self, msg: Message):
        try:
            with engine.begin() as c:
                if msg.author.bot:
                    return

                if msg.guild is None:
                    return

                configured = c.execute(
                    select(chat_summary_channels.c.cid).where(
                        (chat_summary_channels.c.gid == str(msg.guild.id))
                        & (chat_summary_channels.c.cid == str(msg.channel.id))
                    )
                ).fetchone()
                if configured is None:
                    return

                # Count into chat summary
                inc(c, msg)
        except Exception as e:
            akabot_logger.exception(f"Failed to process chat summary message {msg.id}: {e}")

    @loop(minutes=1)
    async def task_summary(self):
        for i in self.bot.guilds:
            try:
                with engine.begin() as c:
                    now = get_now(i.id, c)

                    if now.hour != 0 or now.minute != 0:
                        continue

                    await summarize(c, i)
            except Exception as e:
                akabot_logger.exception(f"Failed to summarize chat for guild {i.id}: {e}")

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
            configured = c.execute(
                select(chat_summary_channels.c.cid).where(
                    (chat_summary_channels.c.gid == str(ctx.guild.id))
                    & (chat_summary_channels.c.cid == str(ctx.channel.id))
                )
            ).fetchone()
            if configured is None:
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
