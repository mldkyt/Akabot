import datetime
import re

import discord
import sentry_sdk

from database import client
from utils.english_words import get_random_english_word, scramble_word


def start_word_scrambler(channel_id: int, message_id: int, word: str) -> str:
    """Starts a word scramble game in a channel"""

    client["WordScramble"].insert_one({"ChannelID": str(channel_id),  # So we know where to update
                                       "MessageID": str(message_id),  # So we know what to update
                                       "Word": word,  # The word to unscramble,
                                       "Expires": datetime.datetime.now() + datetime.timedelta(minutes=5)
                                       # The game expires in 5 minutes
                                       })


def is_word_scrambler_running(channel_id: int) -> bool:
    """Check if a word scramble game is running in a channel"""
    data = client["WordScramble"].find_one({"ChannelID": str(channel_id)})

    if data is None:
        return False

    if data["Expires"] < datetime.datetime.now():
        client["WordScramble"].delete_one({"ChannelID": str(channel_id)})
        return False

    return True


def attempt_guess_word_scrambler(channel_id: int, guess: str) -> bool:
    """Check if the guess is correct and update the message"""
    data = client["WordScramble"].find_one({"ChannelID": str(channel_id)})

    if data is None:
        return False

    if data["Expires"] < datetime.datetime.now():
        client["WordScramble"].delete_one({"ChannelID": str(channel_id)})
        return False

    if data["Word"] == guess:
        return True

    return False


def get_word_scrambler_original_message(channel_id: int) -> int | None:
    """Get the original message ID of the word scramble game"""
    data = client["WordScramble"].find_one({"ChannelID": str(channel_id)})

    if data is None:
        return None

    return data["MessageID"]


def end_word_scrambler(channel_id: int):
    client["WordScramble"].delete_one({"ChannelID": str(channel_id)})


class WordScrambler(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    @discord.slash_command(name="debug_word_scramble", guild_ids=[1234573274504237087])
    async def debug_word_scramble(self, ctx: discord.ApplicationContext):

        try:
            word = get_random_english_word()
            scrambled_word = scramble_word(word)

            msg = await ctx.channel.send("# Word Scramble!\nUnscramble the word below:\n\n`" + scrambled_word + "`")
            start_word_scrambler(ctx.channel.id, msg.id, word)

            await ctx.respond("Word scrambler started", ephemeral=True)
        except Exception as e:
            await ctx.respond("Failed to start word scrambler", ephemeral=True)
            sentry_sdk.capture_exception(e)

    @discord.Cog.listener()
    async def on_message(self, msg: discord.Message):
        try:
            if msg.author.bot:
                return

            if not is_word_scrambler_running(msg.channel.id):
                return

            if re.match(r"^[a-zA-Z]+$", msg.content) is None:
                return

            if attempt_guess_word_scrambler(msg.channel.id, msg.content):
                orig = get_word_scrambler_original_message(msg.channel.id)
                if orig is None:
                    return

                orig = await msg.channel.fetch_message(orig)

                await orig.edit(
                    content="# Word Scramble!\n\nWon by " + msg.author.mention + "\nThe word was: `" + msg.content + "`")
                await msg.reply("Correct! The word was: `" + msg.content + "`")

                end_word_scrambler(msg.channel.id)
        except Exception as e:
            sentry_sdk.capture_exception(e)
