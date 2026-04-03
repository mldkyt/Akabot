from datetime import date

from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Member,
    Message,
    SlashCommandGroup,
)
from discord.ext.pages import Paginator

from database import engine
from logger import nekona_logger
from utils.chat_streaks import (
    get_all_streaks_for,
    get_guild_link,
    get_leaderboard,
    get_streak,
    get_unexpired_streak,
    server_message_delay,
    update_for_user,
    handle_send_reply, user_response_setting, server_response_setting
)
from utils.docs import Docs, DocsCommand, DocsSetting
from utils.server_settings import SettingType, settings
from utils.user_settings import user_settings


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

                    if user_response_setting.get(c, msg.author) in ["expiry", "on"]:
                        a = await handle_send_reply(
                            msg, f"**Awww :( your chat streak expired.** It was {unex_streak} days before it did."
                        )
                        if a is not None:
                            await a.delete(delay=int(server_message_delay.get(c, msg.author)))
                    return
                if next_streak > prev_streak:
                    if user_response_setting.get(c, msg.author) == "on":
                        a = await handle_send_reply(
                            msg,
                            f"**{next_streak} days of consecutive messages!** Keep it up!\n-# Disable using `/user_settings`."
                        )
                        if a is not None:
                            await a.delete(delay=int(server_message_delay.get(c, msg.author)))
        except Exception as e:
            nekona_logger.exception(e)

    @chat_streaks.command()
    async def streak(self, ctx: ApplicationContext):
        try:
            with engine.begin() as c:
                streak = get_streak(c, ctx.user)

                await ctx.respond(
                    f"Your current streak is {streak} days.", ephemeral=True
                )
        except Exception as e:
            nekona_logger.exception(e)
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
            nekona_logger.exception(e)
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


def setup(bot: Bot):
    bot.add_cog(ChatStreaks(bot))

    settings.add_settings(server_response_setting, server_message_delay)

    user_settings.add_settings(user_response_setting)


def docs():
    return str(
        Docs(
            name="Chat Streaks",
            description="Chat Streaks allow you to see how chronically online are your members. It counts consecutive days of chatting. A chat streak is lost when the member skips a day.",
            commands=[
                DocsCommand(
                    command="chat_streaks leaderboard",
                    description="View the leaderboard. The leaderboard has arrows to navigate back and forth.",
                ),
                DocsCommand(
                    command="chat_streaks streak",
                    description="View the amount of days on your streak.",
                ),
            ],
            settings=[
                DocsSetting(
                    name="Chat streaks disable response",
                    description="Both a server and user setting. The server setting disables Chat Streak responses for everyone, the user setting disabled it on all servers for you.",
                    setting_type=SettingType.NORMAL,
                ),
                DocsSetting(
                    name="Chat streaks message duration",
                    description="A server setting that configures how long the response is shown for.",
                    setting_type=SettingType.NORMAL,
                ),
            ],
        )
    )
