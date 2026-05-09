from discord import Cog, Bot, slash_command, ApplicationContext, Embed

from utils.fun import yaoi_cache, yuri_cache


class Fun(Cog):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    @slash_command()
    async def yaoi(self, ctx: ApplicationContext):
        yaoi_post = await yaoi_cache.get_yaoibot_post()
        if yaoi_post is None:
            await ctx.respond("Yaoi is unavailable.", ephemeral=True)
            return

        embed = Embed(
            title="Yaoi!",
            image=yaoi_post["files"][0]["url"]
        )

        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command()
    async def yuri(self, ctx: ApplicationContext):
        yuri_post = await yuri_cache.get_yuribot_post()
        if yuri_post is None:
            await ctx.respond("Yuri is unavailable.", ephemeral=True)
            return

        embed = Embed(
            title="Yuri!",
            image=yuri_post["files"][0]["url"]
        )

        await ctx.respond(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(Fun(bot))
