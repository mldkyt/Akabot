import discord
from discord.ext.pages import Paginator

from database import engine
from utils.docs import Docs, DocsCommand, DocsCommandParameter
from utils.user_settings import (
    user_setting_name_autocomplete,
    user_setting_name_list_autocomplete,
    user_settings,
)


class UserSettings(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()

        self.bot = bot

    user_settings_gr = discord.SlashCommandGroup(name="user_settings")

    @user_settings_gr.command()
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=user_setting_name_autocomplete,
    )
    @discord.option(name="value", description="Value to set")
    async def set_setting(self, ctx: discord.ApplicationContext, name: str, value: str):
        """Set a setting"""

        setting = user_settings.get_setting(name)
        if setting is None:
            return

        with engine.begin() as c:
            ok, value = setting.process_add(c, ctx.user, value)
            if not ok:
                await ctx.respond(value, ephemeral=True)
                return

            setting.validate_and_set(c, ctx.user, value)

            response = setting.respond_add(c, ctx.user, value)
            await ctx.respond(response, ephemeral=True)

    @user_settings_gr.command()
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=user_setting_name_autocomplete,
    )
    async def get_setting(self, ctx: discord.ApplicationContext, name: str):
        """Set a setting"""

        setting = user_settings.get_setting(name)
        if setting is None:
            return

        with engine.begin() as c:
            value = setting.get(c, ctx.guild.id)

        await ctx.respond(f"{name} is currently {value}", ephemeral=True)

    @user_settings_gr.command()
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=user_setting_name_list_autocomplete,
    )
    async def add_list_setting(
        self, ctx: discord.ApplicationContext, name: str, value: str
    ):
        """Add an element into a list setting"""

        setting = user_settings.get_setting(name)
        if setting is None:
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

    @user_settings_gr.command()
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=user_setting_name_list_autocomplete,
    )
    async def remove_list_setting(
        self, ctx: discord.ApplicationContext, name: str, value: str
    ):
        """Remove an element from a list setting"""

        setting = user_settings.get_setting(name)
        if setting is None:
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

    @user_settings_gr.command()
    @discord.option(
        name="name",
        description="Name of setting",
        autocomplete=user_setting_name_list_autocomplete,
    )
    async def clear_list_setting(self, ctx: discord.ApplicationContext, name: str):
        """Clear a list setting"""

        setting = user_settings.get_setting(name)
        if setting is None:
            return

        with engine.begin() as c:
            setting.clear_list(c, ctx.user)

        await ctx.respond(f"Cleared settings for list setting {name}", ephemeral=True)

    @user_settings_gr.command()
    async def list_settings(self, ctx: discord.ApplicationContext):
        """Set a setting"""
        with engine.begin() as c:
            sets = user_settings.list_user_settings_pretty(c, ctx.user)

        pages = []
        page = ""
        for i in range(len(sets)):
            page += f"- {sets[i]}\n"
            if i % 5 == 4:
                pages.append(page)
                page = ""

        if len(page) > 0:
            pages.append(page)

        paginator = Paginator(pages)
        await paginator.respond(ctx.interaction, ephemeral=True)


def setup(bot: discord.Bot):
    bot.add_cog(UserSettings(bot))


def docs():
    return str(
        Docs(
            name="User Settings",
            description="User settings help you adjust the Akabot settings for yourself. There are 2 types of settings: normal settings and list settings. Available settings for each module of Akabot can be read under the respective page. Use the sidebar.",
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
