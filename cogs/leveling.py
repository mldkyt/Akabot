import discord
from discord import ApplicationContext

from database import engine
from utils.docs import Docs, DocsCommand, DocsSetting
from utils.leveling import get_xp, add_xp, calculate_level, apply_leveling_rewards, setting_xp_per_message, \
    setting_level_up_message, setting_xp_per_level, \
    setting_leveling_rewards, xp_to_next_level, setting_leveling_multipliers, get_multiplier
from utils.server_settings import settings, SettingType


class Leveling(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()

        self.bot = bot

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
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

            if settings.get_setting("Leveling enable level-up message").get(c, message.author) == "true":
                if old_level != new_level:
                    await apply_leveling_rewards(c, message.author)

                    level_up_message = await message.reply(f"**You leveled up!** {old_level} -> {new_level}")
                    await level_up_message.delete(delay=5)

    @discord.slash_command()
    async def level(self, ctx: ApplicationContext):
        """Get your current level"""
        with engine.begin() as c:
            xp = get_xp(c, ctx.user.id, ctx.guild.id)
            level = calculate_level(c, ctx.user, xp)
            to_next_level = xp_to_next_level(c, ctx.user, xp)
            xp_per_level = int(setting_xp_per_level.get(c, ctx.user))

            await ctx.respond(f"You're on level {level}. {to_next_level}/{xp_per_level} ({(to_next_level / xp_per_level) * 100:.2f}%) XP for next level\n"
                              f"The current multiplier is {get_multiplier(c, ctx.user)}x.", ephemeral=True)

def setup(bot):
    bot.add_cog(Leveling(bot))

    settings.add_settings(
        setting_xp_per_message,
        setting_level_up_message,
        setting_xp_per_level,
        setting_leveling_rewards,
        setting_leveling_multipliers
    )


def docs():
    return str(
        Docs(
            "Leveling",
            description="Adds levels, level-up rewards and more fun into your server.",
            commands=[
                DocsCommand(
                    "level",
                    description="Show user level"
                )
            ],
            settings=[
                DocsSetting(
                    "Leveling XP per message",
                    setting_type=SettingType.NORMAL,
                    description="How much XP to set per message"
                ),
                DocsSetting(
                    "Leveling enable level-up message",
                    setting_type=SettingType.NORMAL,
                    description="Whether to enable a brief \"Level Up\" message"
                ),
                DocsSetting(
                    "Leveling XP per level",
                    setting_type=SettingType.NORMAL,
                    description="How much XP is required per level"
                ),
                DocsSetting(
                    "Leveling rewards",
                    setting_type=SettingType.LIST,
                    description="Reward stuff for levels",
                    add_description="The format `<role>, <level>` is required."
                ),
                DocsSetting(
                    "Leveling multipliers",
                    setting_type=SettingType.LIST,
                    description="Time-based leveling multipliers.",
                    add_description="Must follow the format `<MM-DD> - <MM-DD>, <multiplier>`. Adds a multiplier.",
                    remove_description="Format `MM-DD - MM-DD`. Removes the multiplier."
                )
            ]
        )
    )
