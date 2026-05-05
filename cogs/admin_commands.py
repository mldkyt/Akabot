import os

from discord import Cog, Bot, SlashCommandGroup, ApplicationContext

from utils.admin import CreateMailModal

ADMIN_GUILD = int(os.getenv("ADMIN_GUILD", "0"))


class AdminCommands(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    admin_group = SlashCommandGroup("admin", guild_ids=[ADMIN_GUILD])

    @admin_group.command()
    async def create_mail(self, ctx: ApplicationContext):
        await ctx.response.send_modal(CreateMailModal())


def setup(bot: Bot):
    if ADMIN_GUILD != 0:
        bot.add_cog(AdminCommands(bot))
