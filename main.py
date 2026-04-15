import asyncio
import os

import fluxer
from dotenv import load_dotenv

from logger import nekona_logger

BOT_VERSION = "@VERSION@"


bot = fluxer.Bot()


@bot.event
async def on_ready():
    nekona_logger.info(f"Ready as {bot.user.username}#{bot.user.discriminator}")


async def load_extensions():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            nekona_logger.info(f"Loading cogs.{filename[:-3]}")
            await bot.load_extension(f"cogs.{filename[:-3]}")
    nekona_logger.info("Cogs loaded")


if __name__ == "__main__":
    if not os.path.exists("logs"):
        os.mkdir("logs")

    load_dotenv()

    nekona_logger.info(f"Nekona {BOT_VERSION}-fluxer is starting up")

    asyncio.run(load_extensions())
    bot.run(os.getenv("FLUXER_TOKEN"))
