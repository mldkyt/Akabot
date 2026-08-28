import datetime

from discord import ButtonStyle, Interaction
from discord.ui import Button, View, button
from sqlalchemy import select, update

from database import chat_streaks, engine, vote_points


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


class ReviveChatStreakView(View):
    def __init__(self, user_id: str, days: int):
        super().__init__(timeout=1800, disable_on_timeout=True)

        self.days = days
        self.user_id = user_id

        self.revive_streak_btn = Button(
            label=f"Revive my {days} day streak!", style=ButtonStyle.secondary
        )
        self.revive_streak_btn.callback = self.revive_chat_streak
        self.add_item(self.revive_streak_btn)

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

        with engine.begin() as c:
            c.execute(
                update(chat_streaks)
                .where(
                    (chat_streaks.c.gid == str(interaction.guild.id))
                    & (chat_streaks.c.uid == str(interaction.user.id))
                )
                .values(
                    last_message_date=datetime.datetime.now(datetime.UTC).date(),
                    start_date=(
                        datetime.datetime.now(datetime.UTC)
                        - datetime.timedelta(days=self.days)
                    ).date(),
                )
            )

        add_voting_points(str(interaction.user.id), -10)
        points = get_voting_points(str(interaction.user.id))

        await interaction.respond(
            f"Your {self.days} day streak was revived for 10 Vote Points! :3\nYou now have {points} Vote Points",
            ephemeral=True,
        )

        self.disable_all_items()
        self.stop()
        await interaction.message.edit(view=self)
