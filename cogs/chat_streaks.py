from datetime import datetime

from discord import Cog, Bot, Message, slash_command, ApplicationContext, SlashCommandGroup
from discord.ext.pages import Paginator

from database import engine
from logger import nekona_logger
from utils.chat_streaks import update_for_user, get_streak, server_disable_response, user_disable_response, \
    get_leaderboard, server_message_delay
from utils.docs import Docs, DocsCommand, DocsSetting
from utils.server_settings import settings, SettingType
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

            with engine.begin() as c:
                prev_streak = get_streak(c, msg.author)
                update_for_user(c, msg.author)
                next_streak = get_streak(c, msg.author)

                if server_disable_response.get(c, msg.author) == "true":
                    return

                if user_disable_response.get(c, msg.author) == "true":
                    return

                if next_streak > prev_streak:
                    a = await msg.reply(
                        f"**{next_streak} days of consecutive messages!** Keep it up!\n-# Disable using `/user_settings`.")
                    await a.delete(delay=int(server_message_delay.get(c, msg.author)))
        except Exception as e:
            nekona_logger.exception(e)

    @chat_streaks.command()
    async def streak(self, ctx: ApplicationContext):
        try:
            with engine.begin() as c:
                streak = get_streak(c, ctx.user)

                await ctx.respond(f"Your current streak is {streak} days.", ephemeral=True)
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

def setup(bot: Bot):
    bot.add_cog(ChatStreaks(bot))

    settings.add_settings(
        server_disable_response,
        server_message_delay
    )

    user_settings.add_settings(
        user_disable_response
    )

def docs():
    return str(
        Docs(
            name="Chat Streaks",
            description="Chat Streaks allow you to see how chronically online are your members. It counts consecutive days of chatting. A chat streak is lost when the member skips a day.",
            commands=[
                DocsCommand(
                    command="chat_streaks leaderboard",
                    description="View the leaderboard. The leaderboard has arrows to navigate back and forth."
                ),
                DocsCommand(
                    command="chat_streaks streak",
                    description="View the amount of days on your streak."
                )
            ],
            settings=[
                DocsSetting(
                    name="Chat streaks disable response",
                    description="Both a server and user setting. The server setting disables Chat Streak responses for everyone, the user setting disabled it on all servers for you.",
                    setting_type=SettingType.NORMAL
                ),
                DocsSetting(
                    name="Chat streaks message duration",
                    description="A server setting that configures how long the response is shown for.",
                    setting_type=SettingType.NORMAL
                )
            ]
        )
    )
