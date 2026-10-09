import logging
import os

import discord
import sentry_sdk
from discord.ext import commands as commands_ext
from dotenv import load_dotenv
from sentry_sdk.integrations.logging import LoggingIntegration

from logger import akabot_logger

if not os.path.exists("logs"):
    os.mkdir("logs")

load_dotenv()

if os.getenv("SENTRY_SDK"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_SDK"),
        integrations=[
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=1,
        auto_session_tracking=False,
        send_default_pii=True,
    )

BOT_VERSION = "@VERSION@"

akabot_logger.info(f"Akabot {BOT_VERSION} is starting up")


intents = discord.Intents.default()
intents.members = True

if os.getenv("MESSAGE_INTENT", "0") == "1":
    intents.message_content = True

bot = discord.Bot(intents=intents)

for filename in os.listdir("cogs"):
    if filename.endswith(".py"):
        bot.load_extension(f"cogs.{filename[:-3]}")
        akabot_logger.info(f"Loading cogs.{filename[:-3]}")

akabot_logger.info("Cogs loaded")


@bot.event
async def on_ready():
    akabot_logger.info(f"Ready as {bot.user.name}#{bot.user.discriminator}")

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing, name=f"Akabot {BOT_VERSION}"
        )
    )


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    if isinstance(error, commands_ext.CommandOnCooldown):
        minutes = int(error.retry_after / 60)
        seconds = int(error.retry_after % 60)
        if minutes > 0:
            await ctx.respond(
                f"**Cooldown!** {minutes} minutes and {seconds} seconds remaining",
                ephemeral=True,
            )
        else:
            await ctx.respond(
                f"**Cooldown!** {seconds} seconds remaining", ephemeral=True
            )
        return

    if isinstance(error, commands_ext.MissingPermissions):
        await ctx.respond(
            f"You do not have permission to use this command. Missing {', '.join(error.missing_permissions)}",
            ephemeral=True,
        )
        return

    if isinstance(error, commands_ext.NoPrivateMessage):
        await ctx.respond("This command cannot be used in DMs", ephemeral=True)
        return

    if isinstance(error, commands_ext.BotMissingPermissions):
        await ctx.respond(
            f"The bot has missing permissions! Missing permissions: {', '.join(error.missing_permissions)}",
            ephemeral=True,
        )
        return

    if isinstance(error, commands_ext.PrivateMessageOnly):
        await ctx.respond("This command can only be used in DMs.", ephemeral=True)
        return

    try:
        # respond
        await ctx.respond("An error occured", ephemeral=True)
    except Exception:
        akabot_logger.exception("Failed to respond to message")

    sentry_sdk.capture_exception(error)
    raise error


bot.run(os.getenv("DISCORD_TOKEN"))
