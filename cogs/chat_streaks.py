import datetime
from datetime import date

import sentry_sdk
from discord import (
    ApplicationContext,
    Bot,
    ButtonStyle,
    Cog,
    Forbidden,
    HTTPException,
    Interaction,
    Member,
    Message,
    SlashCommandGroup,
    User,
    option,
)
from discord.ext.pages import Paginator
from discord.ext.tasks import loop
from discord.ui import View, button

from database import engine
from utils.chat_streaks import (
    get_all_streaks_for,
    get_expiring_streaks,
    get_guild_link,
    get_leaderboard,
    get_raw_streak,
    get_streak,
    get_unexpired_streak,
    handle_send_reply,
    server_message_delay,
    update_for_user,
    user_response_setting,
    user_setting_receive_notifications,
)
from utils.message_appends import apply_appends
from utils.voting import ChatStreakExpireView, get_voting_points


class EnableDMNotificationsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="Enable DM notifications",
        style=ButtonStyle.green,
        custom_id="chatstreaksdmenable",
    )
    async def enable_dm_notifications(self, button, interaction: Interaction):
        assert isinstance(interaction.user, User)

        with engine.begin() as c:
            if user_setting_receive_notifications.get(c, interaction.user.id) == "true":
                await interaction.respond(
                    "DM notifications are already enabled", ephemeral=True
                )
                return

            user_setting_receive_notifications.set(c, interaction.user.id, "true")

        await interaction.respond(
            "DM notifications were enabled. You can disable them using `/chat_streaks dm_notifications`.",
            ephemeral=True,
        )


class UnsubscribeDMNotificationsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="Disable DM notifications",
        style=ButtonStyle.red,
        custom_id="chatstreaksdmdisable",
    )
    async def disable_dm_notifications(self, button, interaction: Interaction):
        assert isinstance(interaction.user, User)

        with engine.begin() as c:
            if user_setting_receive_notifications.get(c, interaction.user.id) != "true":
                await interaction.respond(
                    "DM notifications are already disabled", ephemeral=True
                )
                return

            user_setting_receive_notifications.set(c, interaction.user.id, "false")

        await interaction.respond(
            "DM notifications were disabled. You can re-enable them using `/chat_streaks dm_notifications`."
        )


class ChatStreaks(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    chat_streaks = SlashCommandGroup(name="chat_streaks")

    @Cog.listener()
    async def on_ready(self):
        self.chat_streak_reminders.start()

        self.bot.add_view(UnsubscribeDMNotificationsView())
        self.bot.add_view(EnableDMNotificationsView())

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
                raw_streak = get_raw_streak(c, msg.author)
                prev_streak = get_streak(c, msg.author)
                update_for_user(c, msg.author)
                next_streak = get_streak(c, msg.author)

                if unex_streak != prev_streak:
                    if user_response_setting.get(c, msg.author.id) in ["expiry", "on"]:
                        p = get_voting_points(str(msg.author.id))
                        the_reply, reply_in_same_channel = await handle_send_reply(
                            msg,
                            apply_appends(
                                msg.author.id,
                                f"**Awww :( your chat streak expired.** It was {unex_streak} days before it did.",
                            ),
                            view=(
                                ChatStreakExpireView(str(msg.author.id), unex_streak)
                                if (p > 10 and raw_streak - unex_streak <= 2)
                                or user_setting_receive_notifications.get(
                                    c, msg.author.id
                                )
                                == "true"
                                else None
                            ),
                        )
                        if (
                            the_reply is not None
                            and reply_in_same_channel
                            and p <= 10
                            and raw_streak - unex_streak > 2
                        ):
                            await the_reply.delete(
                                delay=int(server_message_delay.get(c, msg.guild.id))
                            )
                    return
                if next_streak > prev_streak:
                    if user_response_setting.get(c, msg.author.id) == "on":
                        dm_notifications_enabled = (
                            user_setting_receive_notifications.get(c, msg.author.id)
                            == "true"
                        )
                        the_reply, reply_in_same_channel = await handle_send_reply(
                            msg,
                            apply_appends(
                                msg.author.id,
                                f"**{next_streak} days of consecutive messages!** Keep it up!\n-# Disable using `/chat_streaks alerts`.",
                            ),
                            view=(
                                EnableDMNotificationsView()
                                if not dm_notifications_enabled
                                else None
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
        if ctx.guild is None:
            await ctx.respond("This is not a command for DM's", ephemeral=True)
            return

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

    @chat_streaks.command()
    @option("notif_type", choices=["on", "off"])
    async def dm_notifications(self, ctx: ApplicationContext, notif_type: str):
        """Set DM notifications preference to another setting"""
        with engine.begin() as c:
            user_setting_receive_notifications.set(
                c, ctx.user.id, "true" if notif_type == "on" else "false"
            )

        await ctx.respond(
            f"DM reminders from all servers are now {notif_type}",
            ephemeral=True,
        )

    async def run_chat_streak_reminders(self):
        with engine.begin() as c:
            async for gid, uid in get_expiring_streaks(c):
                guild = self.bot.get_guild(int(gid))
                if guild is None:
                    continue

                member = guild.get_member(int(uid))
                if member is None:
                    try:
                        member = await guild.fetch_member(int(uid))
                    except HTTPException:
                        continue

                dm_preference = user_setting_receive_notifications.get(c, member.id)
                if dm_preference != "true":
                    continue

                streak = get_streak(c, member)

                if streak < 3:  # Remind only of streaks that are worth something
                    continue

                try:
                    await member.send(
                        f"Your {streak} day streak in {guild.name} is about to expire! Save it before it expires.",
                        view=UnsubscribeDMNotificationsView(),
                    )
                except Forbidden:
                    pass

    @loop(seconds=60)
    async def chat_streak_reminders(self):
        try:
            now = datetime.datetime.now(datetime.UTC)

            if now.hour != 12 or now.minute != 0:
                return

            await self.run_chat_streak_reminders()
        except Exception as e:
            sentry_sdk.capture_exception(e)


def setup(bot: Bot):
    bot.add_cog(ChatStreaks(bot))
