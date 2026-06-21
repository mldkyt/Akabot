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
                    c, ctx.user, value
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
                    c, ctx.user, value
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


def docs():
    return str(
        Docs(
            name="Server Settings",
            description="Server settings help you adjust the Akabot settings for your server. There are 2 types of settings: normal settings and list settings. Available settings for each module of Akabot can be read under the respective page. Use the sidebar.",
            commands=[
                DocsCommand(
                    command="set_setting",
                    description="Sets a setting to a value",
                    parameters=[
                        DocsCommandParameter(
                            name="name",
                            description="The name of the setting to set. Use the dropdown to choose",
                        ),
                        DocsCommandParameter(
                            name="value",
                            description="The value to set it to. In the case of an invalid value, the bot will tell you.",
                        ),
                    ],
                ),
                DocsCommand(
                    command="get_setting",
                    description="Get a setting's value",
                    parameters=[
                        DocsCommandParameter(
                            name="name",
                            description="The name of the setting to get. Use the dropdown to choose.",
                        )
                    ],
                ),
                DocsCommand(
                    command="list_settings",
                    description="List all settings available in Akabot and their current values.",
                ),
                DocsCommand(
                    command="add_list_setting",
                    description="Add a value to a list setting.",
                    parameters=[
                        DocsCommandParameter(
                            name="name",
                            description="The name of the list setting to add to. Use the dropdown to choose",
                        ),
                        DocsCommandParameter(
                            name="value",
                            description="The value to add. In the case of an invalid value, the bot will tell you.",
                        ),
                    ],
                ),
                DocsCommand(
                    command="remove_list_setting",
                    description="Remove a value from a list setting.",
                    parameters=[
                        DocsCommandParameter(
                            name="name",
                            description="The name of the list setting to remove from. Use the dropdown to choose",
                        ),
                        DocsCommandParameter(
                            name="value",
                            description="The value to remove. In the case of an invalid value, the bot will tell you.",
                        ),
                    ],
                ),
                DocsCommand(
                    command="clear_list_setting",
                    description="Remove all values from a list setting.",
                    parameters=[
                        DocsCommandParameter(
                            name="name",
                            description="The name of the list setting to remove from. Use the dropdown to choose",
                        )
                    ],
                ),
            ],
        )
    )
