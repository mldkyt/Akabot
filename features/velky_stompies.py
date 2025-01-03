#      Akabot is a general purpose bot with a ton of features.
#      Copyright (C) 2023-2025 mldchan
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
import discord
import sentry_sdk
from discord.ext import commands

from utils.logging_util import log_into_logs
from utils.settings import get_setting, set_setting


class VelkyStompies(discord.Cog):
    @discord.slash_command(name="stompies", description="Velky's stompies command")
    async def velky_stompies(self, ctx: discord.ApplicationContext):
        try:
            if get_setting(ctx.guild.id, "stompies_enabled", "True") == "False":
                await ctx.respond("The command is disabled", ephemeral=True)
                return

            await ctx.respond("https://tenor.com/view/stompies-velky-cute-angwy-gif-13012534518393437613")
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond("Something went wrong", ephemeral=True)

    stompies_settings_group = discord.SlashCommandGroup("stompies_settings", "Stompies commands")

    @stompies_settings_group.command(name="enable", description="Set the enabled state of the Velky Stompies command")
    @discord.option(name="enabled", description="Whether the Velky stompies command is enabled", type=bool)
    @discord.default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    async def stompies_enable(self, ctx: discord.ApplicationContext, enabled: bool):
        try:
            old_value = get_setting(ctx.guild.id, "stompies_enabled", str(enabled)) == "True"

            if old_value != enabled:
                logging_embed = discord.Embed(title="Stompies enabled changed")
                logging_embed.add_field(name="User", value=f"{ctx.user.mention}")
                logging_embed.add_field(name="Value",
                                        value=f'{"Enabled" if old_value else "Disabled"} -> {"Enabled" if enabled else "Disabled"}')

                await log_into_logs(ctx.guild, logging_embed)

            set_setting(ctx.guild.id, 'stompies_enabled', str(enabled))

            await ctx.respond(f'Succcessfully turned on stompies' if enabled else 'Successfully turned off stompies',
                              ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond("Something went wrong", ephemeral=True)
