import datetime
import logging
import random
import re

import discord
import sentry_sdk
from discord.ext import commands, tasks

from database import client
from utils.english_words import get_random_english_word, scramble_word
from utils.languages import get_translation_for_key_localized as trl
from utils.leveling import get_level_for_xp, add_xp, get_xp, update_roles_for_member
from utils.settings import get_setting, set_setting


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

    return True


def attempt_guess_word_scrambler(channel_id: int, guess: str) -> bool:
    """Check if the guess is correct and update the message"""
    data = client["WordScramble"].find_one({"ChannelID": str(channel_id)})

    if data is None:
        return False

    if data["Expires"] < datetime.datetime.now():
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


async def get_word_by_context(channel: discord.TextChannel):
    if channel is None:
        raise ValueError("Channel is None")

    chan_conf = get_setting(channel.guild.id, "word_scramble_channels", {})
    chan_conf = chan_conf[str(channel.id)]
    if "context" not in chan_conf:
        return get_random_english_word()

    if chan_conf["context"] == "english":
        return get_random_english_word()

    if chan_conf["context"] == "channel":
        words = []
        if not channel.permissions_for(channel.guild.me).read_message_history:
            return get_random_english_word()
        async for message in channel.history(limit=100):
            if message.author.bot:
                continue
            words_iter = re.findall(r"[a-zA-Z]+", message.content)
            for i in words_iter:
                if chan_conf['min'] < len(i) < chan_conf['max']:
                    words.append(i.lower())

        return random.choice(words) if words else get_random_english_word()

    if chan_conf["context"] == "all_channels":
        words = []
        for channel in channel.guild.text_channels:
            if not channel.permissions_for(channel.guild.me).read_message_history:
                continue
            async for message in channel.history(limit=100):
                if message.author.bot:
                    continue
                words_iter = re.findall(r"[a-zA-Z]+", message.content)
                for i in words_iter:
                    if chan_conf['min'] < len(i) < chan_conf['max']:
                        words.append(i.lower())

        return random.choice(words) if words else get_random_english_word()

    logging.warning("Invalid context for word scramble")
    return get_random_english_word()


class WordScrambler(discord.Cog):
    def __init__(self, bot: discord.Bot):
        super().__init__()
        self.bot = bot

    @discord.Cog.listener()
    async def on_ready(self):
        self.random_word_scramble_task.start()
        self.cleanup_task.start()

    word_scramble_commands = discord.SlashCommandGroup(name="word_scramble", description="Word Scramble commands")

    @word_scramble_commands.command(name="start", description="Force start a word scramble game in this channel")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def word_scramble_start(self, ctx: discord.ApplicationContext):
        try:
            await ctx.defer(ephemeral=True)

            if is_word_scrambler_running(ctx.channel.id):
                await ctx.respond("A word scramble game is already running in this channel", ephemeral=True)
                return

            word = await get_word_by_context(ctx.channel)
            scrambled_word = scramble_word(word)

            role = get_setting(ctx.guild.id, "word_scramble_ping_role", None)
            if role is not None:
                role = ctx.guild.get_role(role)

            msg = await ctx.channel.send(
                "# Word Scramble!\nUnscramble the word below:\n\n`" + scrambled_word + "`" + (f"\n\n{role.mention}" if role is not None else ""))
            start_word_scrambler(ctx.channel.id, msg.id, word)

            await ctx.followup.send("Word scrambler started", ephemeral=True)
        except Exception as e:
            await ctx.respond("Failed to start word scrambler", ephemeral=True)
            sentry_sdk.capture_exception(e)

    @word_scramble_commands.command(name="end", description="Force end a word scramble game in this channel")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def word_scramble_end(self, ctx: discord.ApplicationContext):
        try:
            if not is_word_scrambler_running(ctx.channel.id):
                await ctx.respond("No word scramble game is running in this channel", ephemeral=True)
                return

            message = get_word_scrambler_original_message(ctx.channel.id)
            if message is not None:
                message = await ctx.channel.fetch_message(message)
                await message.edit(content="Word scramble game ended forcibly by " + ctx.author.mention)

            end_word_scrambler(ctx.channel.id)
            await ctx.respond("Word scrambler ended", ephemeral=True)
        except Exception as e:
            await ctx.respond("Failed to end word scrambler", ephemeral=True)
            sentry_sdk.capture_exception(e)

    @word_scramble_commands.command(name="set_channel", description="Add a channel or set settings for word scramble")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @discord.option(name="chance", description="One in what chance to start per minute? Higher value = Less occurence",
                    type=int, required=True)
    @discord.option(name="min", description="Minimum word length", type=int, required=True)
    @discord.option(name="max", description="Maximum word length", type=int, required=True)
    @discord.option(name="context", description="Context for word scramble", type=str, required=True,
                    choices=["english", "channel messages", "messages in all channels"])
    async def word_scramble_set_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel,
                                        chance: int, min_characters: int, max_characters: int, context: str):
        try:
            if min_characters < 3:
                await ctx.respond("Minimum word length must be at least 3", ephemeral=True)
                return

            if max_characters > 20:
                await ctx.respond("Maximum word length must be at most 20", ephemeral=True)
                return

            if min_characters > max_characters:
                await ctx.respond("Minimum word length must be less than or equal to maximum word length",
                                  ephemeral=True)
                return

            if chance < 1:
                await ctx.respond("Chance must be at least 1", ephemeral=True)
                return

            if context == "channel messages":
                context = "channel"
            elif context == "messages in all channels":
                context = "all_channels"

            if context not in ["english", "channel", "all_channels"]:  # Extra check just in case
                await ctx.respond("Invalid context", ephemeral=True)
                return

            sett = get_setting(ctx.guild.id, "word_scramble_channels", {})
            sett[str(channel.id)] = {"chance": chance, "min": min_characters, "max": max_characters, "context": context}

            set_setting(ctx.guild.id, "word_scramble_channels", sett)
            await ctx.respond(f"Channel set\n"
                              f"**Chance**: 1 in {chance} chance\n"
                              f"**Minimum Letters**: {min_characters}\n"
                              f"**Maximum Letters**: {max_characters}\n", ephemeral=True)
        except Exception as e:
            await ctx.respond("Failed to set channel", ephemeral=True)
            sentry_sdk.capture_exception(e)

    @word_scramble_commands.command(name="set_xp_per_game", description="Set XP to add per game won in word scramble")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def word_scramble_set_xp(self, ctx: discord.ApplicationContext, xp: int | None = None):
        if xp is None:
            await ctx.respond(
                "Current XP per game: " + str(get_setting(ctx.guild.id, "leveling_xp_per_word_scrambler", 100)),
                ephemeral=True)
            return

        else:
            if xp < 0:
                await ctx.respond("XP must be at least 0", ephemeral=True)
                return

            set_setting(ctx.guild.id, "leveling_xp_per_word_scrambler", xp)
            await ctx.respond("XP per game set", ephemeral=True)

    @word_scramble_commands.command(name="remove_channel", description="Remove a channel from word scramble")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def word_scramble_remove_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            sett = get_setting(ctx.guild.id, "word_scramble_channels", {})
            if channel.id in sett:
                del sett[str(channel.id)]
                set_setting(ctx.guild.id, "word_scramble_channels", sett)
                await ctx.respond("Channel removed", ephemeral=True)
            else:
                await ctx.respond("Channel not found", ephemeral=True)
        except Exception as e:
            await ctx.respond("Failed to remove channel", ephemeral=True)
            sentry_sdk.capture_exception(e)

    @word_scramble_commands.command(name="set_role", description="Set a ping role for word scramble")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def word_scramble_set_role(self, ctx: discord.ApplicationContext, role: discord.Role | None = None,
                                     unset: bool = False):
        if role is None:
            if unset:
                set_setting(ctx.guild.id, "word_scramble_ping_role", None)
                await ctx.respond("Role unset", ephemeral=True)
                return

            await ctx.respond("Current role: " + str(get_setting(ctx.guild.id, "word_scramble_ping_role", "None")),
                              ephemeral=True)
            return

        set_setting(ctx.guild.id, "word_scramble_ping_role", role.id)
        await ctx.respond("Role set", ephemeral=True)

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

                xp = get_setting(msg.guild.id, "leveling_xp_per_word_scrambler", 100)

                await orig.edit(content=f"# Word Scramble!\n"
                                        f"\n"
                                        f"Won by {msg.author.mention}"
                                        f"\nThe word was: `{msg.content}`")
                rep = await msg.reply(
                    f"Correct! The word was: `{msg.content}`" if xp == 0 else f"Correct! The word was: `{msg.content}`"
                                                                              f"\nYou earned {xp} XP!")
                await rep.delete(delay=5)

                # Leveling
                before_level = get_level_for_xp(msg.guild.id, get_xp(msg.guild.id, msg.author.id))
                add_xp(msg.guild.id, msg.author.id, get_setting(msg.guild.id, "leveling_xp_per_word_scrambler", 100))
                after_level = get_level_for_xp(msg.guild.id, get_xp(msg.guild.id, msg.author.id))

                if not msg.channel.permissions_for(msg.guild.me).send_messages:
                    return

                if msg.guild.me.guild_permissions.manage_roles:
                    await update_roles_for_member(msg.guild, msg.author)

                if before_level != after_level and msg.channel.can_send():
                    msg2 = await msg.channel.send(
                        trl(msg.author.id, msg.guild.id, "leveling_level_up").format(mention=msg.author.mention,
                                                                                     level=str(after_level)))
                    await msg2.delete(delay=5)

                end_word_scrambler(msg.channel.id)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @tasks.loop(minutes=1)
    async def random_word_scramble_task(self):
        await self.random_word_scramble()

    async def random_word_scramble(self):
        for guild in self.bot.guilds:
            channels = get_setting(guild.id, "word_scramble_channels", {})
            for channel_id, settings in channels.items():
                channel_id = int(channel_id)
                if is_word_scrambler_running(channel_id):
                    continue

                rand = random.randint(1, settings["chance"])
                if rand == 1:
                    word = await get_word_by_context(guild.get_channel(channel_id))
                    if len(word) < settings["min"] or len(word) > settings["max"]:
                        continue

                    scrambled_word = scramble_word(word)
                    channel = self.bot.get_channel(channel_id)
                    if channel is None:
                        continue

                    role = get_setting(guild.id, "word_scramble_ping_role", None)
                    if role is not None:
                        role = guild.get_role(role)

                    msg = await channel.send(
                        "# Word Scramble!\nUnscramble the word below:\n\n`" + scrambled_word + "`" + (f"\n\n{role.mention}" if role is not None else ""))
                    start_word_scrambler(channel_id, msg.id, word)

    @tasks.loop(minutes=1)
    async def cleanup_task(self):
        await self.cleanup()

    async def cleanup(self):
        expired = client["WordScramble"].find({"Expires": {"$lt": datetime.datetime.now()}})
        for game in expired:
            channel = self.bot.get_channel(int(game["ChannelID"]))
            if channel is None:
                continue

            message = await channel.fetch_message(int(game["MessageID"]))
            await message.edit(content=f"# Word Scramble!\n\n"
                                       f"Game over! The word was: `{game['Word']}`! Better luck next time!")
            end_word_scrambler(int(game["ChannelID"]))
