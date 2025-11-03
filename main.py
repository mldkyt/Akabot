from logger import nekona_logger
import os

import discord

from dotenv import load_dotenv



if not os.path.exists("logs"):
    os.mkdir("logs")




load_dotenv()

BOT_VERSION = "0.0.1"

nekona_logger.info(f"Nekona {BOT_VERSION} is starting up")

bot = discord.Bot()

for filename in os.listdir('cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')
        nekona_logger.info(f"Loading cogs.{filename[:-3]}")

nekona_logger.info("Cogs loaded")

@bot.event
async def on_ready():
    nekona_logger.info(f"Ready as {bot.user.name}#{bot.user.discriminator}")

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"Nekona {BOT_VERSION}"))

bot.run(os.getenv("DISCORD_TOKEN"))
