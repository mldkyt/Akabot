import datetime

import discord
from discord.ext import commands as commands_ext
from discord.ext import tasks

from database import conn as db
from utils.analytics import analytics
from utils.blocked import is_blocked


class ChatSummary(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        global chat_summary_old
        super().__init__()
        cur = db.cursor()
        cur.execute("PRAGMA table_info(chat_summary)")
        # Check if the format is correct, there should be 4 columns of info, if not, delete and recreate table.
        chat_summary_cols = len(cur.fetchall())

        cur.execute("SELECT * FROM chat_summary")
        chat_summary_old = cur.fetchall()
        if chat_summary_cols != 4:
            print("DEBUG recreating table chat_summary, row count", chat_summary_cols, "is not 4")
            print("Loading records...", end='')
            print(len(chat_summary_old), "records fetched.")

            cur.execute("DROP TABLE chat_summary")

        cur.execute(
            'CREATE TABLE IF NOT EXISTS chat_summary(guild_id INTEGER, channel_id INTEGER, enabled INTEGER, messages INTEGER)')
        cur.execute(
            'CREATE INDEX IF NOT EXISTS chat_summary_i ON chat_summary(guild_id, channel_id)')

        for i in chat_summary_old:
            cur.execute("insert into chat_summary(guild_id, channel_id, enabled, messages) values (?, ?, ?, ?)",
                        (i[0], i[1], i[2], i[3]))

        cur.execute(
            'CREATE TABLE IF NOT EXISTS chat_summary_members(guild_id INTEGER, channel_id INTEGER, member_id INTEGER, messages INTEGER)')
        cur.execute(
            'CREATE INDEX IF NOT EXISTS chat_summary_members_i ON chat_summary_members(guild_id, channel_id, member_id)')
        cur.close()
        db.commit()
        self.bot = bot

    @discord.Cog.listener()
    @is_blocked()
    async def on_message(self, message: discord.Message):
        if message.guild is None:
            return
        cur = db.cursor()
        cur.execute('SELECT * FROM chat_summary WHERE guild_id = ? AND channel_id = ?',
                    (message.guild.id, message.channel.id))
        if not cur.fetchone():
            cur.execute(
                'INSERT INTO chat_summary(guild_id, channel_id, enabled, messages) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (message.guild.id, message.channel.id, 0, 0, 0, 0, 0))

        # Increment total message count
        cur.execute('UPDATE chat_summary SET messages = messages + 1 WHERE guild_id = ? AND channel_id = ?',
                    (message.guild.id, message.channel.id))

        # Increment message count for specific member
        cur.execute('SELECT * FROM chat_summary_members WHERE guild_id = ? AND channel_id = ? AND member_id = ?',
                    (message.guild.id, message.channel.id, message.author.id))
        if not cur.fetchone():
            cur.execute(
                'INSERT INTO chat_summary_members(guild_id, channel_id, member_id, messages) VALUES (?, ?, ?, ?)',
                (message.guild.id, message.channel.id, message.author.id, 0))

        cur.execute(
            'UPDATE chat_summary_members SET messages = messages + 1 WHERE guild_id = ? AND channel_id = ? AND member_id = ?',
            (message.guild.id, message.channel.id, message.author.id))

        cur.close()
        db.commit()

    @tasks.loop(minutes=1)
    async def summarize(self):
        now = datetime.datetime.now(datetime.UTC)
        if now.hour != 0 or now.minute != 0:
            return

        cur = db.cursor()
        cur.execute('SELECT guild_id, channel_id, messages FROM chat_summary WHERE enabled = 1')
        for i in cur.fetchall():
            guild = self.bot.get_guild(i[0])
            if guild is None:
                continue

            channel = guild.get_channel(i[1])
            if channel is None:
                continue

            now = datetime.datetime.now(datetime.timezone.utc)
            chat_summary_message = f'# Chat Summary for {now.month}/{now.day}/{now.year}:\n'
            chat_summary_message += '\n'
            chat_summary_message += f'**Messages**: {i[2]}\n'

            cur.execute(
                'SELECT member_id, messages FROM chat_summary_members WHERE guild_id = ? AND channel_id = ? ORDER BY '
                'messages DESC LIMIT 5', (i[0], i[1]))

            jndex = 0  # idk
            for j in cur.fetchall():
                jndex += 1
                member = guild.get_member(j[0])
                if member is not None:
                    chat_summary_message += f'{jndex}. {member.display_name} at {j[1]} messages\n'
                else:
                    chat_summary_message += f'{jndex}. User({j[0]}) at {j[1]} messages\n'

            await channel.send(chat_summary_message)

            cur.execute('UPDATE chat_summary SET messages = 0, WHERE guild_id = ? AND channel_id = ?', (i[0], i[1]))
            cur.execute(
                'DELETE FROM chat_summary_members WHERE guild_id = ? AND channel_id = ?', (i[0], i[1]))

        cur.close()
        db.commit()

    chat_summary_subcommand = discord.SlashCommandGroup(
        name='chatsummary', description='Chat summary')

    @chat_summary_subcommand.command(name="add", description="Add a channel to count to chat summary")
    @commands_ext.guild_only()
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.bot_has_permissions(send_messages=True)
    @is_blocked()
    @analytics("chatsummary add")
    async def command_add(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        cur = db.cursor()
        cur.execute('SELECT * FROM chat_summary WHERE guild_id = ? AND channel_id = ?',
                    (ctx.guild.id, channel.id))
        if not cur.fetchone():
            cur.execute(
                'INSERT INTO chat_summary(guild_id, channel_id, enabled, messages) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (ctx.guild.id, channel.id, 0, 0, 0, 0, 0))

        cur.execute('SELECT enabled FROM chat_summary WHERE guild_id = ? AND channel_id = ?',
                    (ctx.guild.id, channel.id))
        data = cur.fetchone()
        if data is not None and data[0] == 1:
            await ctx.response.send_message("This channel is already being counted.", ephemeral=True)
            return

        cur.execute('UPDATE chat_summary SET enabled = 1 WHERE guild_id = ? AND channel_id = ?',
                    (ctx.guild.id, channel.id))
        cur.close()
        db.commit()

        await ctx.response.send_message('Added channel to counting.', ephemeral=True)

    @chat_summary_subcommand.command(name="remove", description="Remove a channel from being counted to chat summary")
    @commands_ext.guild_only()
    @commands_ext.has_permissions(manage_guild=True)
    @is_blocked()
    @analytics("chatsummary remove")
    async def command_remove(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        cur = db.cursor()
        cur.execute('SELECT * FROM chat_summary WHERE guild_id = ? AND channel_id = ?',
                    (ctx.guild.id, channel.id))
        if not cur.fetchone():
            cur.execute(
                'INSERT INTO chat_summary(guild_id, channel_id, enabled, messages) VALUES (?, ?, ?, '
                '?)',
                (ctx.guild.id, channel.id, 0, 0))
        cur.execute('SELECT enabled FROM chat_summary WHERE guild_id = ? AND channel_id = ?',
                    (ctx.guild.id, channel.id))
        data = cur.fetchone()
        if data is not None and data[0] == 0:
            await ctx.response.send_message("This channel is already not being counted.", ephemeral=True)
            return

        cur.execute('UPDATE chat_summary SET enabled = 0 WHERE guild_id = ? AND channel_id = ?',
                    (ctx.guild.id, channel.id))
        cur.close()
        db.commit()

        await ctx.response.send_message('Removed channel from being counted.', ephemeral=True)

    # The commented code below is for testing purposes
    # @chat_summary_subcommand.command(name="test", description="Test command for testing purposes")
    # @commands_ext.guild_only()
    # @commands_ext.has_permissions(manage_guild=True)
    # @is_blocked()
    # async def test_summarize(self, ctx: discord.ApplicationContext):
    #     cur = db.cursor()
    #     cur.execute('SELECT guild_id, channel_id, messages FROM chat_summary WHERE enabled = 1')
    #     for i in cur.fetchall():
    #         guild = self.bot.get_guild(i[0])
    #         if guild is None:
    #             continue
    #
    #         channel = guild.get_channel(i[1])
    #         if channel is None:
    #             continue
    #
    #         now = datetime.datetime.now(datetime.timezone.utc)
    #         chat_summary_message = f'# Chat Summary for {now.month}/{now.day}/{now.year}:\n'
    #         chat_summary_message += '\n'
    #         chat_summary_message += f'**Messages**: {i[2]}\n'
    #         chat_summary_message += f'OwOs: {i[3]}\n'
    #         chat_summary_message += f'Nya~\'s: {i[4]}\n'
    #         chat_summary_message += f':3\'s: {i[5]}\n\n**Top members:**\n'
    #
    #         cur.execute(
    #             'SELECT member_id, messages FROM chat_summary_members WHERE guild_id = ? AND channel_id = ? ORDER BY '
    #             'messages DESC LIMIT 5', (i[0], i[1]))
    #
    #         jndex = 0
    #         for j in cur.fetchall():
    #             jndex += 1
    #             member = guild.get_member(j[0])
    #             if member is not None:
    #                 chat_summary_message += f'{jndex}. {member.display_name} at {j[1]} messages\n'
    #             else:
    #                 chat_summary_message += f'{jndex}. User({j[0]}) at {j[1]} messages\n'
    #
    #         await channel.send(chat_summary_message)
    #
    #         cur.execute('UPDATE chat_summary SET messages = 0, WHERE guild_id = ? AND'
    #                     ' channel_id = ?', (i[0], i[1]))
    #         cur.execute('DELETE FROM chat_summary_members WHERE guild_id = ? AND channel_id = ?', (i[0], i[1]))
    #
    #     cur.close()
    #     db.commit()
    #
    #     await ctx.response.send_message('InDev', ephemeral=True)
