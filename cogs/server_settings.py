import discord
from discord.ext.pages import Paginator

from database import engine
from utils.docs import Docs, DocsCommand, DocsCommandParameter
from utils.server_settings import (
    setting_name_autocomplete,
    setting_name_list_autocomplete,
    settings,
)


class ServerSettings(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()

        self.bot = bot

    server_settings = discord.SlashCommandGroup(name="server_settings")

    @server_settings.command()
    @discord.default_permissions(manage_guild=True)
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=setting_name_autocomplete,
    )
    @discord.option(name="value", description="Value to set")
    async def set_setting(self, ctx: discord.ApplicationContext, name: str, value: str):
        """Set a setting"""

        setting = settings.get_setting(name)
        if setting is None:
            return

        if ctx.guild is None:
            await ctx.respond("This command is for servers", ephemeral=True)
            return

        with engine.begin() as c:
            ok, value = setting.process_add(c, ctx.user, value)
            if not ok:
                await ctx.respond(value, ephemeral=True)
                return

            setting.validate_and_set(c, ctx.user, value)

            response = setting.respond_add(c, ctx.user, value)
            await ctx.respond(response, ephemeral=True)

    @server_settings.command()
    @discord.default_permissions(manage_guild=True)
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=setting_name_autocomplete,
    )
    async def get_setting(self, ctx: discord.ApplicationContext, name: str):
        """Set a setting"""

        setting = settings.get_setting(name)
        if setting is None:
            return

        if ctx.guild is None:
            await ctx.respond("This command is for servers", ephemeral=True)
            return

        with engine.begin() as c:
            value = setting.get(c, ctx.guild.id)

        await ctx.respond(f"{name} is currently {value}", ephemeral=True)

    @server_settings.command()
    @discord.default_permissions(manage_guild=True)
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=setting_name_list_autocomplete,
    )
    async def add_list_setting(
        self, ctx: discord.ApplicationContext, name: str, value: str
    ):
        """Add an element into a list setting"""

        setting = settings.get_setting(name)
        if setting is None:
            return

        if ctx.guild is None:
            await ctx.respond("This command is for servers", ephemeral=True)
            return

        with engine.begin() as c:
            ok, value = setting.process_add(c, ctx.user, value)
            if not ok:
                await ctx.respond(value, ephemeral=True)
                return

            if setting.is_in_list(
                    c, ctx.guild.id, value
            ):
                await ctx.respond(
                    f"The value {value} is already in the list {name}", ephemeral=True
                )
                return

            setting.add_to_list(c, ctx.guild.id, value)

            response = setting.respond_add(c, ctx.user, value)
            await ctx.respond(response, ephemeral=True)

    @server_settings.command()
    @discord.default_permissions(manage_guild=True)
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=setting_name_list_autocomplete,
    )
    async def remove_list_setting(
        self, ctx: discord.ApplicationContext, name: str, value: str
    ):
        """Add an element into a list setting"""

        setting = settings.get_setting(name)
        if setting is None:
            return

        if ctx.guild is None:
            await ctx.respond("This command is for servers", ephemeral=True)
            return

        with engine.begin() as c:
            ok, value = setting.process_remove(c, ctx.user, value)
            if not ok:
                await ctx.respond(value, ephemeral=True)
                return

            if not setting.is_in_list(
                    c, ctx.guild.id, value
            ):
                await ctx.respond(
                    f"The value {value} is not in the list {name}", ephemeral=True
                )
                return

            setting.remove_from_list(c, ctx.user, value)

            response = setting.respond_remove(c, ctx.user, value)
            await ctx.respond(response, ephemeral=True)

    @server_settings.command()
    @discord.default_permissions(manage_guild=True)
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=setting_name_list_autocomplete,
    )
    async def clear_list_setting(self, ctx: discord.ApplicationContext, name: str):
        """Add an element into a list setting"""

        setting = settings.get_setting(name)
        if setting is None:
            return

        if ctx.guild is None:
            await ctx.respond("This command is for servers", ephemeral=True)
            return

        with engine.begin() as c:
            setting.clear_list(c, ctx.user)

        await ctx.respond(f"Cleared settings for list setting {name}", ephemeral=True)

    @server_settings.command()
    @discord.default_permissions(manage_guild=True)
    async def list_settings(self, ctx: discord.ApplicationContext):
        """Set a setting"""
        if ctx.guild is None:
            await ctx.respond("This command is for servers", ephemeral=True)
            return

        with engine.begin() as c:
            sets = settings.list_server_settings_pretty(c, ctx.user)

        pages = []
        page = ""
        for i in sets:
            if len(page) + len(i) + 3 > 1000:
                pages.append(page)
                page = ""

            page += f"- {i}\n"

        if len(page) > 0:
            pages.append(page)

        paginator = Paginator(pages)
        await paginator.respond(ctx.interaction, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(ServerSettings(bot))
