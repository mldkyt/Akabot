from discord import ApplicationContext, Bot, Cog, slash_command
from sqlalchemy import select

from database import engine, vote_points
from utils.ads import VoteBotAd


class Voting(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @slash_command()
    async def vote(self, ctx: ApplicationContext):
        """Vote for the bot!"""

        await ctx.respond(
            "Vote for the bot today and get Voting Points!",
            ephemeral=True,
            view=VoteBotAd(),
        )

    @slash_command()
    async def vote_points(self, ctx: ApplicationContext):
        """See how many vote points you have!"""

        with engine.begin() as c:
            p = c.execute(
                select(vote_points.c.points).where(
                    vote_points.c.uid == str(ctx.user.id)
                )
            ).fetchone()

            if not p:
                p = [0]

            p = p[0]

        await ctx.respond(f"You currently have {p} Vote Points.", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Voting(bot))
