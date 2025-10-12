import os

import discord

from dotenv import load_dotenv

load_dotenv()

bot = discord.Bot()

for filename in os.listdir('cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_ready():
    print(f"Ready as {bot.user.name}#{bot.user.discriminator}")

    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=f"Nekona 0.1.0"))

bot.run(os.getenv("DISCORD_TOKEN"))
