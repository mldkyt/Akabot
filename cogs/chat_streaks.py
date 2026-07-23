from datetime import date

import sentry_sdk
from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Member,
    Message,
    SlashCommandGroup,
    option,
)
from discord.ext.pages import Paginator

from database import engine
from utils.chat_streaks import (
    get_all_streaks_for,
    get_guild_link,
    get_leaderboard,
    get_streak,
    get_unexpired_streak,
    handle_send_reply,
    server_message_delay,
    update_for_user,
    user_response_setting,
)
from utils.message_appends import apply_appends


class ChatStreaks(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    chat_streaks = SlashCommandGroup(name="chat_streaks")

    @Cog.listener()
    async def on_message(self, msg: Message):
        try:
            if msg.author.bot:
                return
            if msg.guild is None:
                return
            if not isinstance(msg.author, Member):
                return

            with engine.begin() as c:
                unex_streak = get_unexpired_streak(c, msg.author)
                prev_streak = get_streak(c, msg.author)
                update_for_user(c, msg.author)
                next_streak = get_streak(c, msg.author)

                if unex_streak != prev_streak:
                    if user_response_setting.get(c, msg.author.id) in ["expiry", "on"]:
                        the_reply, reply_in_same_channel = await handle_send_reply(
                            msg,
                            apply_appends(
                                msg.author.id,
                                f"**Awww :( your chat streak expired.** It was {unex_streak} days before it did.",
                            ),
                        )
                        if the_reply is not None and reply_in_same_channel:
                            await the_reply.delete(
                                delay=int(server_message_delay.get(c, msg.guild.id))
                            )
                    return
                if next_streak > prev_streak:
                    if user_response_setting.get(c, msg.author.id) == "on":
                        the_reply, reply_in_same_channel = await handle_send_reply(
                            msg,
                            apply_appends(
                                msg.author.id,
                                f"**{next_streak} days of consecutive messages!** Keep it up!\n-# Disable using `/user_settings`.",
                            ),
                        )
                        if the_reply is not None and reply_in_same_channel:
                            await the_reply.delete(
                                delay=int(server_message_delay.get(c, msg.guild.id))
                            )
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @chat_streaks.command()
    async def streak(self, ctx: ApplicationContext):
        try:
            with engine.begin() as c:
                streak = get_streak(c, ctx.user)

                await ctx.respond(
                    apply_appends(
                        ctx.user.id, f"Your current streak is {streak} days."
                    ),
                    ephemeral=True,
                )
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond("Error", ephemeral=True)

    @chat_streaks.command()
    async def leaderboard(self, ctx: ApplicationContext):
        try:
            with engine.begin() as c:
                lb = get_leaderboard(c, ctx.user)

                pages = []
                page = "# Chat Streak Leaderboard\n"

                for i in range(len(lb)):
                    v = lb[i]
                    days = v[2] - v[1]

                    page += f"{i + 1}. <@{v[0]}> with {days.days} days of consecutive messages\n"

                    if (i + 1) % 10 == 0:
                        pages.append(page)
                        page = ""

                if len(page) > 0:
                    pages.append(page)

                paginator = Paginator(pages)
                await paginator.respond(ctx.interaction, ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond("Error", ephemeral=True)

    @chat_streaks.command()
    async def my_chat_streaks(self, ctx: ApplicationContext):
        with engine.begin() as c:
            my_chat_streaks_fetched = get_all_streaks_for(c, self.bot, ctx.user)

            pages: list[str] = []
            curpage = "# My Chat Streaks\n"

            for i in range(len(my_chat_streaks_fetched)):
                guild = self.bot.get_guild(int(my_chat_streaks_fetched[i][0]))
                if guild is None:
                    continue

                guild_link = get_guild_link(guild)

                days_from_now = date.today() - my_chat_streaks_fetched[i][2]

                if days_from_now.days == 0:
                    indicator = "🔥"
                elif days_from_now.days == 1:
                    indicator = "⚠️"
                else:
                    indicator = "❌"

                guild_name = (
                    f"**[{guild.name}]({guild_link.jump_url})**"
                    if guild_link is not None
                    else f"**{guild.name}**"
                )

                days = my_chat_streaks_fetched[i][2] - my_chat_streaks_fetched[i][1]
                curpage += f"- {indicator} {guild_name} - {days.days} days\n"
                if i % 5 == 4:
                    pages.append(curpage)
                    curpage = ""

            if len(curpage.strip()) > 17:
                pages.append(curpage)

            paginator = Paginator(pages)
            await paginator.respond(ctx.interaction, ephemeral=True)

    @chat_streaks.command()
    @option("notif_type", choices=["on", "expiry", "off"])
    async def alerts(self, ctx: ApplicationContext, notif_type: str):
        """Set alert notification to another setting"""
        with engine.begin() as c:
            user_response_setting.set(c, ctx.user.id, notif_type)

        await ctx.respond(
            f"Your notification state for chat streak alerts was set to {notif_type}",
            ephemeral=True,
        )


def setup(bot: Bot):
    bot.add_cog(ChatStreaks(bot))
