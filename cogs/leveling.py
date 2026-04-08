import discord
from discord import ApplicationContext, Message

from database import engine
from logger import nekona_logger
from utils.docs import Docs, DocsCommand
from utils.leveling import (
    add_xp,
    apply_leveling_rewards,
    calculate_level,
    get_multiplier,
    get_xp,
    setting_level_up_message,
    setting_leveling_multipliers,
    setting_leveling_rewards,
    setting_xp_per_level,
    setting_xp_per_message,
    xp_to_next_level, setting_level_up_message_text,
)
from utils.server_settings import settings


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

                if setting_level_up_message.get(c, message.author) == "true":
                    if old_level != new_level:
                        await apply_leveling_rewards(c, message.author)

                        level_up_message = setting_level_up_message_text.get(c, message.author)

                        level_up_message = level_up_message.replace("{old}", str(old_level))
                        level_up_message = level_up_message.replace("{new}", str(new_level))
                        level_up_message = level_up_message.replace("{mention}", message.author.mention)
                        level_up_message = level_up_message.replace("{server}", message.guild.name)
                        level_up_message = level_up_message.replace("{name}", message.author.display_name)
                        level_up_message = level_up_message.replace("{username}", message.author.name)

                        level_up_message = await message.reply(level_up_message)
                        await level_up_message.delete(delay=5)
        except Exception as e:
            nekona_logger.exception(e)

    @discord.slash_command()
    async def level(self, ctx: ApplicationContext):
        """Get your current level"""
        try:
            with engine.begin() as c:
                xp = get_xp(c, ctx.user.id, ctx.guild.id)
                level = calculate_level(c, ctx.user, xp)
                to_next_level = xp_to_next_level(c, ctx.user, xp)
                xp_per_level = int(setting_xp_per_level.get(c, ctx.user))

                await ctx.respond(
                    f"You're on level {level}. {to_next_level}/{xp_per_level} ({(to_next_level / xp_per_level) * 100:.2f}%) XP for next level\n"
                    f"The current multiplier is {get_multiplier(c, ctx.user)}x.",
                    ephemeral=True,
                )
        except Exception as e:
            nekona_logger.exception(e)
            await ctx.respond("Error", ephemeral=True)


def setup(bot):
    bot.add_cog(Leveling(bot))

    settings.add_settings(
        setting_xp_per_message,
        setting_level_up_message,
        setting_level_up_message_text,
        setting_xp_per_level,
        setting_leveling_rewards,
        setting_leveling_multipliers,
    )


def docs():
    return str(
        Docs(
            "Leveling",
            description="Adds levels, level-up rewards and more fun into your server.",
            commands=[DocsCommand("level", description="Show user level")],
            settings=[
                setting_xp_per_message,
                setting_level_up_message,
                setting_level_up_message_text,
                setting_xp_per_level,
                setting_leveling_rewards,
                setting_leveling_multipliers
            ],
        )
    )
