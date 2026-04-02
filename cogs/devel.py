import os

from discord import Bot, Cog, SlashCommandGroup, ApplicationContext

from logger import nekona_logger
from utils.ads import get_ad


class Devel(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    devel_group = SlashCommandGroup(name="devel", guild_ids=[int(os.getenv("DEVEL_GUILD_ID", "0"))])

    @devel_group.command()
    async def ad_test(self, ctx: ApplicationContext):
        await ctx.respond("Test", view=get_ad())


def setup(bot: Bot):
    if os.getenv("DEVEL", "0") != "1":
        return

    if len(os.getenv("DEVEL_GUILD_ID", "").strip()) == 0:
        nekona_logger.warning("Devel mode is on, but commands were not loaded due to missing guild id.")
        return

    bot.add_cog(Devel(bot))
