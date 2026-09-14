import sentry_sdk
from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Member,
    Message,
    SlashCommandGroup,
)
from discord.ext.commands import BucketType, cooldown
from discord.ext.pages import Paginator
from sqlalchemy import select

from cogs.web import WEB_DOMAIN
from database import engine, message_counting, message_counting_members
from logger import akabot_logger
from utils.message_counting import (
    dec,
    inc,
    reindex,
    setting_enable_indexer,
    setting_enable_leaderboard,
    update_roles, setting_count_deletes,
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

                await update_roles(c, msg)
        except Exception as e:
            akabot_logger.exception(f"Failed to process message counting for message {msg.id}: {e}")
            sentry_sdk.capture_exception(e)

    @Cog.listener()
    async def on_message_delete(self, msg: Message):
        try:
            with engine.begin() as c:
                if msg.author.bot:
                    return

                if msg.guild is None:
                    return

                delete_setting = setting_count_deletes.get(c, msg.guild.id)
                if delete_setting != "true":
                    return

                dec(c, msg)

                await update_roles(c, msg)
        except Exception as e:
            akabot_logger.exception(f"Failed to process message delete counting for message {msg.id}: {e}")
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
            enable_leaderboard = (
                setting_enable_leaderboard.get(c, ctx.guild.id) == "true"
            )

            if not enable_leaderboard:
                await ctx.respond("The leaderboard is not enabled", ephemeral=True)
                return

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
            current_page = f"# Message Counting Leaderboard - {data_total[0]} messages\n\n[Also view on website!](https://{WEB_DOMAIN}/leaderboard/{ctx.guild_id})\n\n"

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

    @message_counting_cmds.command()
    @cooldown(rate=1, per=3600, type=BucketType.guild)
    async def index(self, ctx: ApplicationContext):
        """Reindex the current channel. Requires admin permission and the indexer to be enabled."""

        if not ctx.guild or not isinstance(ctx.user, Member):
            await ctx.respond(
                "This command is meant to only be ran in guilds.", ephemeral=True
            )
            return

        with engine.begin() as c:
            if setting_enable_indexer.get(c, ctx.guild.id) != "true":
                await ctx.respond(
                    "The index command is disabled in the settings", ephemeral=True
                )
                return

        if not ctx.user.guild_permissions.manage_guild:
            await ctx.respond(
                "This command requires Manage Guild permission.", ephemeral=True
            )
            return

        await ctx.respond(
            "Reindex queued. When the action is finished, a message will be sent here.",
            ephemeral=True,
        )
        message_count = await reindex(ctx.guild)
        await ctx.channel.send(
            f"{ctx.user.mention}, server was reindexed with {message_count} messages."
        )


def setup(bot: Bot):
    bot.add_cog(MessageCounting(bot))
