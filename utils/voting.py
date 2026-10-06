import datetime

from discord import ButtonStyle, Interaction
from discord.ui import Button, View
from sqlalchemy import select, update

from database import chat_streaks, engine, vote_points
from utils.chat_streaks import user_setting_receive_notifications
from utils.timezones import get_now


def get_voting_points(user_id: str) -> int:
    with engine.begin() as c:
        p = c.execute(
            select(vote_points.c.points).where(vote_points.c.uid == user_id)
        ).fetchone()

        if not p:
            p = [0]

        p = p[0]

    return p


def add_voting_points(user_id: str, points: int):
    with engine.begin() as c:
        c.execute(
            update(vote_points)
            .where(vote_points.c.uid == user_id)
            .values(points=vote_points.c.points + points)
        )


class ChatStreakExpireView(View):
    def __init__(self, user_id: str, days: int):
        super().__init__(timeout=1800, disable_on_timeout=True)

        with engine.begin() as c:
            points = get_voting_points(user_id)
            dm_notifications = (
                user_setting_receive_notifications.get(c, int(user_id)) == "true"
            )

        self.days = days
        self.user_id = user_id

        if points >= 10:
            self.revive_streak_btn = Button(
                label=f"Revive my {days} day streak!", style=ButtonStyle.secondary
            )
            self.revive_streak_btn.callback = self.revive_chat_streak
            self.add_item(self.revive_streak_btn)

        if not dm_notifications:
            self.enable_notifications_btn = Button(
                label="Enable DM notifications", style=ButtonStyle.secondary
            )
            self.enable_notifications_btn.callback = self.enable_notifications
            self.add_item(self.enable_notifications_btn)

    async def revive_chat_streak(self, interaction: Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.respond(
                "This message is not targeted at you", ephemeral=True
            )
            return

        points = get_voting_points(str(interaction.user.id))
        if points < 10:
            await interaction.respond(
                "You do not have enough Voting Points for this item. You need to vote for the bot more in order to revive your chat streak",
                ephemeral=True,
            )
            return

        if interaction.guild is None:
            return

        with engine.begin() as c:
            now = get_now(interaction.guild.id, c)
            c.execute(
                update(chat_streaks)
                .where(
                    (chat_streaks.c.gid == str(interaction.guild.id))
                    & (chat_streaks.c.uid == str(interaction.user.id))
                )
                .values(
                    last_message_date=now.date(),
                    start_date=(now - datetime.timedelta(days=self.days)).date(),
                )
            )

        add_voting_points(str(interaction.user.id), -10)
        points = get_voting_points(str(interaction.user.id))

        await interaction.respond(
            f"Your {self.days} day streak was revived for 10 Vote Points! :3\nYou now have {points} Vote Points",
            ephemeral=True,
        )

        self.revive_streak_btn.disabled = True
        await interaction.message.edit(view=self)

    async def enable_notifications(self, interaction: Interaction):
        assert interaction.user is not None

        with engine.begin() as c:
            if user_setting_receive_notifications.get(c, interaction.user.id) == "true":
                await interaction.respond(
                    "Your DM notifications are already enabled", ephemeral=True
                )
                return

            user_setting_receive_notifications.set(c, interaction.user.id, "true")

        await interaction.respond("DM notifications were enabled", ephemeral=True)
