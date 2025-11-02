import logging
import os

import discord

from dotenv import load_dotenv

nekona_logger = logging.getLogger("nekona")
nekona_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

nekona_logger.setLevel(logging.DEBUG)

if not os.path.exists("logs"):
    os.mkdir("logs")

file_handler = logging.FileHandler(filename="logs/nekona.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(nekona_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(nekona_formatter)

nekona_logger.addHandler(file_handler)
nekona_logger.addHandler(console_handler)


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
