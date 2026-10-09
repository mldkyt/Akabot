import discord
from discord import ApplicationContext, Member, Message, Permissions, SlashCommandGroup

from database import engine
from logger import akabot_logger
from utils.chat_streaks import handle_send_reply
from utils.leveling import (
    add_xp,
    apply_leveling_rewards,
    calculate_level,
    edit_xp,
    edit_xp_rel,
    get_multiplier,
    get_xp,
    setting_level_up_message,
    setting_level_up_message_text,
    setting_xp_per_level,
    xp_to_next_level,
)
from utils.message_appends import apply_appends


class Leveling(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()

        self.bot = bot

    @discord.Cog.listener()
    async def on_message(self, message: Message):
        try:
            if message.guild is None:
                return

            if message.author.bot:
                return

            with engine.begin() as c:
                old_xp = get_xp(c, message.author.id, message.guild.id)
                add_xp(c, message.author)
                new_xp = get_xp(c, message.author.id, message.guild.id)

                old_level = calculate_level(c, message.author, old_xp)
                new_level = calculate_level(c, message.author, new_xp)

                if setting_level_up_message.get(c, message.guild.id) == "true":
                    if old_level != new_level:
                        await apply_leveling_rewards(c, message.author)

                        level_up_message = setting_level_up_message_text.get(
                            c, message.guild.id
                        )

                        level_up_message = level_up_message.replace(
                            "{old}", str(old_level)
                        )
                        level_up_message = level_up_message.replace(
                            "{new}", str(new_level)
                        )
                        level_up_message = level_up_message.replace(
                            "{mention}", message.author.mention
                        )
                        level_up_message = level_up_message.replace(
                            "{server}", message.guild.name
                        )
                        level_up_message = level_up_message.replace(
                            "{name}", message.author.display_name
                        )
                        level_up_message = level_up_message.replace(
                            "{username}", message.author.name
                        )

                        (
                            level_up_message,
                            reply_in_same_channel,
                        ) = await handle_send_reply(
                            message, apply_appends(message.author.id, level_up_message)
                        )
                        if level_up_message is not None and reply_in_same_channel:
                            await level_up_message.delete(delay=5)
        except Exception as e:
            akabot_logger.exception(f"Failed to process level up for message {message.id}: {e}")

    @discord.slash_command()
    async def level(self, ctx: ApplicationContext):
        """Get your current level"""
        try:
            with engine.begin() as c:
                xp = get_xp(c, ctx.user.id, ctx.guild.id)
                level = calculate_level(c, ctx.user, xp)
                to_next_level = xp_to_next_level(c, ctx.user, xp)
                xp_per_level = int(setting_xp_per_level.get(c, ctx.guild.id))

                await ctx.respond(
                    apply_appends(
                        ctx.user.id,
                        f"You're on level {level}. {to_next_level}/{xp_per_level} ({(to_next_level / xp_per_level) * 100:.2f}%) XP for next level\n"
                        f"The current multiplier is {get_multiplier(c, ctx.user)}x.",
                    ),
                    ephemeral=True,
                )
        except Exception as e:
            akabot_logger.exception(f"Failed to fetch level for user {ctx.user.id} in guild {ctx.guild.id}: {e}")
            await ctx.respond("Error", ephemeral=True)

    admin_commands = SlashCommandGroup(
        name="leveling_admin", default_member_permissions=Permissions(manage_guild=True)
    )

    @admin_commands.command()
    async def add_xp(self, ctx: ApplicationContext, user: Member, xp: int):
        """Add XP to a member. Use responsibly."""

        with engine.begin() as c:
            edit_xp_rel(c, user, xp)

        await ctx.respond(f"Added {xp} XP to {user.mention}", ephemeral=True)

    @admin_commands.command()
    async def add_levels(self, ctx: ApplicationContext, user: Member, levels: int):
        """Add levels to a member. Use responsibly."""
        with engine.begin() as c:
            level_xp = int(setting_xp_per_level.get(c, user.guild.id))
            edit_xp_rel(c, user, level_xp * levels)

        await ctx.respond(f"Added {levels} levels to {user.mention}", ephemeral=True)

    @admin_commands.command()
    async def remove_xp(self, ctx: ApplicationContext, user: Member, xp: int):
        """Remove XP from a member. Use responsibly."""
        with engine.begin() as c:
            success, error = edit_xp_rel(c, user, -xp)

        if not success:
            await ctx.respond(error, ephemeral=True)
            return

        await ctx.respond(f"Removed {xp} XP from {user.mention}", ephemeral=True)

    @admin_commands.command()
    async def remove_levels(self, ctx: ApplicationContext, user: Member, levels: int):
        """Remove levels from a member. Use responsibly."""
        with engine.begin() as c:
            level_xp = int(setting_xp_per_level.get(c, user.guild.id))
            success, error = edit_xp_rel(c, user, level_xp * -levels)

        if not success:
            await ctx.respond(error, ephemeral=True)
            return

        await ctx.respond(
            f"Removed {levels} levels from {user.mention}", ephemeral=True
        )

    @admin_commands.command()
    async def set_xp(self, ctx: ApplicationContext, user: Member, xp: int):
        """Set member's XP to a value. Use responsibly."""
        if xp < 0:
            await ctx.respond("Unable to set XP to a negative number", ephemeral=True)
            return

        with engine.begin() as c:
            edit_xp(c, user, xp)

        await ctx.respond(f"Set {user.mention}'s XP to {xp} XP", ephemeral=True)

    @admin_commands.command()
    async def set_levels(self, ctx: ApplicationContext, user: Member, levels: int):
        """Set member's levels to a value. Use responsibly."""
        levels = levels + 1
        if levels < 0:
            await ctx.respond(
                "Unable to set levels to a negative number", ephemeral=True
            )
            return

        with engine.begin() as c:
            level_xp = int(setting_xp_per_level.get(c, user.guild.id))
            edit_xp(c, user, level_xp * levels)

        await ctx.respond(
            f"Set {user.mention}'s level count to {levels - 1} levels", ephemeral=True
        )


def setup(bot):
    bot.add_cog(Leveling(bot))
