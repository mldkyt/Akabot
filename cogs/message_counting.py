import sentry_sdk
from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Message,
    SlashCommandGroup,
)
from discord.ext.pages import Paginator
from sqlalchemy import select

from database import engine, message_counting, message_counting_members
from utils.message_counting import (
    inc,
)


class MessageCounting(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_message(self, msg: Message):
        try:
            with engine.begin() as c:
                if msg.author.bot:
                    return

                if msg.guild is None:
                    return

                # Count into message counting
                inc(c, msg)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    message_counting_cmds = SlashCommandGroup(name="message_counting")

    @message_counting_cmds.command()
    async def leaderboard(self, ctx: ApplicationContext):
        if ctx.guild is None:
            await ctx.respond(
                "This command is only meant to be used in guilds", ephemeral=True
            )
            return

        with engine.begin() as c:
            data_total = c.execute(
                select(message_counting.c.messages).where(
                    message_counting.c.gid == str(ctx.guild.id)
                )
            ).fetchone()

            if not data_total:
                await ctx.respond("There are no messages", ephemeral=True)
                return

            data = c.execute(
                select(
                    message_counting_members.c.uid, message_counting_members.c.messages
                )
                .where(message_counting_members.c.gid == str(ctx.guild.id))
                .order_by(message_counting_members.c.messages.desc())
            ).fetchall()

            pages: list[str] = []
            current_page = (
                f"# Message Counting Leaderboard - {data_total[0]} messages\n\n"
            )

            i = 1
            for j in data:
                username = "Unknown user"
                member = ctx.guild.get_member(int(j[0]))
                if member:
                    username = member.display_name

                current_page += f"{i}. {username} with {j[1]} messages\n"
                i += 1

                if i % 5 == 0:
                    pages.append(current_page)
                    current_page = ""

            if len(current_page) > 0:
                pages.append(current_page)

            pager = Paginator(pages)
            await pager.respond(ctx.interaction, ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(MessageCounting(bot))
