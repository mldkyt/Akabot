import discord
from discord import ApplicationContext, SlashCommandGroup, default_permissions

from utils.message_appends import apply_appends
from utils.premium import has_premium, premium_enabled, redeem_token
from database import engine


class Premium(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    premium_grp = SlashCommandGroup(name="premium", description="Premium commands")

    @premium_grp.command()
    @default_permissions(manage_guild=True)
    async def activate(self, ctx: ApplicationContext, code: str):
        """Activate a premium code for this server"""
        with engine.begin() as c:
            ok, message = redeem_token(c, ctx.guild.id, code)

        if not ok:
            await ctx.respond(f"Could not activate premium: {message}", ephemeral=True)
            return

        await ctx.respond(
            apply_appends(ctx.user.id, f"Premium activated until {message}!"),
            ephemeral=True,
        )

    @premium_grp.command()
    async def status(self, ctx: ApplicationContext):
        """Check the premium status of this server"""
        with engine.begin() as c:
            active = has_premium(c, ctx.guild.id)

        if active:
            await ctx.respond("This server has Premium active!", ephemeral=True)
        else:
            await ctx.respond(
                "This server is on the free plan. Activate a code with /premium activate!",
                ephemeral=True,
            )


def setup(bot: discord.Bot):
    if premium_enabled():
        bot.add_cog(Premium(bot))