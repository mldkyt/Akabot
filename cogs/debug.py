from discord import Cog, Bot, slash_command, ApplicationContext


class Debug(Cog):
    def __init__(self, bot: Bot):
        super().__init__()

        self.bot = bot

    @slash_command(name="debug_print_channels")
    async def print_channels(self, ctx: ApplicationContext):
        message = ""

        for i in ctx.guild.text_channels:
            message += f"{i.mention}: {i.name} {i.position}"

        await ctx.respond(message, ephemeral=True)

def setup(bot: Bot):
    bot.add_cog(Debug(bot))