import discord
from discord.ext.pages import Paginator

from database import engine
from utils.server_settings import set_server_setting, setting_name_autocomplete, get_server_setting, validate_setting, \
    list_server_settings


class ServerSettings(discord.Cog):

    def __init__(self, bot: discord.Bot):
        super().__init__()

        self.bot = bot

    server_settings = discord.SlashCommandGroup(name="server_settings")

    @server_settings.command()
    @discord.default_permissions(manage_guild=True)
    @discord.option(name="name", description="Name of setting", autocomplete=setting_name_autocomplete)
    @discord.option(name="value", description="Value to set")
    async def set_setting(self, ctx: discord.ApplicationContext, name: str, value: str):
        """Set a setting"""

        if ctx.guild is None:
            await ctx.respond("This command is for servers", ephemeral=True)
            return

        if not validate_setting(name, value):
            await ctx.respond(f"Invalid value for {name}", ephemeral=True)
            return

        with engine.begin() as c:
            set_server_setting(c, ctx.guild.id, name, value)

        await ctx.respond(f"Set {name} to {value}", ephemeral=True)

    @server_settings.command()
    @discord.default_permissions(manage_guild=True)
    @discord.option(name="name", description="Name of setting", autocomplete=setting_name_autocomplete)
    async def get_setting(self, ctx: discord.ApplicationContext, name: str):
        """Set a setting"""

        if ctx.guild is None:
            await ctx.respond("This command is for servers", ephemeral=True)
            return

        with engine.begin() as c:
            value = get_server_setting(c, ctx.guild.id, name)

        await ctx.respond(f"{name} is currently {value}", ephemeral=True)

    @server_settings.command()
    @discord.default_permissions(manage_guild=True)
    async def list_settings(self, ctx: discord.ApplicationContext):
        """Set a setting"""

        if ctx.guild is None:
            await ctx.respond("This command is for servers", ephemeral=True)
            return

        with engine.begin() as c:
            sets = list_server_settings(c, ctx.guild.id)

        pages = []
        page = ""
        for i in range(len(sets)):
            page += f"- Setting `{sets[i][0]}` is `{sets[i][1]}`\n"
            if i % 5 == 4:
                pages.append(page)
                page = ""

        if len(page) > 0:
            pages.append(page)

        paginator = Paginator(pages)
        await paginator.respond(ctx.interaction, ephemeral=True)

def setup(bot: discord.Bot):
    bot.add_cog(ServerSettings(bot))
