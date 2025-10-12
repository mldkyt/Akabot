import discord
from database import engine
from utils.leveling import get_xp, add_xp, calculate_level
from utils.server_settings import settings, setting_is_number, setting_is_boolean, setting_to_boolean, \
    get_server_setting

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
            add_xp(c, message.author.id, message.guild.id)
            new_xp = get_xp(c, message.author.id, message.guild.id)

            old_level = calculate_level(c, message.guild.id, old_xp)
            new_level = calculate_level(c, message.guild.id, new_xp)

            if get_server_setting(c, message.guild.id, "Leveling enable level-up message") == "true":
                if old_level != new_level:
                    level_up_message = await message.reply(f"**You leveled up!** {old_level} -> {new_level}")
                    await level_up_message.delete(delay=5)

def setup(bot):
    bot.add_cog(Leveling(bot))

    # Register the setting in the bot
    settings.register_settings(
        "Leveling XP per message",
        "Leveling enable level-up message",
        "Leveling XP per level"
    )

    # Validate users input a number into the settings
    settings.register_validator(
        "Leveling XP per message",
        setting_is_number
    )
    settings.register_validator(
        "Leveling enable level-up message",
        setting_is_boolean
    )
    settings.register_validator(
        "Leveling XP per level",
        setting_is_number
    )

    # Register transformer for boolean value
    settings.register_transformer(
        "Leveling enable level-up message",
        setting_to_boolean
    )

    # Register defaults
    settings.register_defaults(
        ("Leveling XP per message", "3"),
        ("Leveling enable level-up message", "true"),
        ("Leveling XP per level", "500")
    )
