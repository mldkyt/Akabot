from discord import ApplicationContext, Bot, Cog, slash_command

from utils.ads import VoteBotAd
from utils.voting import get_voting_points


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

        points = get_voting_points(str(ctx.user.id))
        await ctx.respond(f"You currently have {points} Vote Points.", ephemeral=True)


def setup(bot: Bot):
    bot.add_cog(Voting(bot))
