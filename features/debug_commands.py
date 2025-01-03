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

from utils.tzutil import get_now_for_server


class DebugCommands(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    dev_commands_group = discord.SlashCommandGroup(name="dev_commands", description="Developer commands")

    @dev_commands_group.command(name="ping", description="Get ping to Discord API")
    async def ping(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Pong! {round(self.bot.latency * 1000)}ms", ephemeral=True)

    @dev_commands_group.command(name="now", description="Get now for server")
    async def now(self, ctx: discord.ApplicationContext):
        await ctx.respond(f"Current time: {get_now_for_server(ctx.guild.id).isoformat()}", ephemeral=True)
