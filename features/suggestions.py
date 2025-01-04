#      Akabot is a general purpose bot with a ton of features.
#      Copyright (C) 2023-2025 mldchan
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from typing import Any

import discord
import sentry_sdk
from discord import Color
from discord.ext import commands
from discord.ui import View

from database import client
from utils.languages import get_translation_for_key_localized as trl
from utils.settings import get_setting, set_setting


def migration_1():
    # Convert user ID's in upvotes and downvotes to strings, if they are not already
    for x in client['SuggestionMessagesV2'].find():
        if all(isinstance(x, str) for x in x['Upvotes']) and all(isinstance(x, str) for x in x['Downvotes']):
            continue

        print('PERFORMING MIGRATION convert upvotes and downvotes to strings')

        upvotes = x['Upvotes']
        downvotes = x['Downvotes']
        client['SuggestionMessagesV2'].update_one({'_id': x['_id']},
                                                  {'$set': {'Upvotes': [str(x) for x in upvotes],
                                                            'Downvotes': [str(x) for x in downvotes]}})


async def perform_basic_checks(interaction: discord.Interaction) -> bool | tuple[bool, Any]:
    data = client['SuggestionMessagesV2'].find_one({'MessageID': str(interaction.message.id)})
    if not data:
        await interaction.response.send_message('This suggestion does not exist in the database', ephemeral=True)
        return False

    if str(interaction.user.id) in data['Upvotes'] or str(interaction.user.id) in data['Downvotes']:
        await interaction.response.send_message('You have already voted on this suggestion', ephemeral=True)
        return False

    return True, data


async def update_existing_suggestions_message(interaction: discord.Interaction):
    suggestions_msg = client['SuggestionMessagesV2'].find_one({'MessageID': str(interaction.message.id)})

    author = interaction.guild.get_member(int(suggestions_msg['AuthorID']))

    new_emb = discord.Embed(title='Suggestion', color=Color.blue(),
                            author=discord.EmbedAuthor(name=f'{author.display_name}\'s suggestion',
                                                       icon_url=author.display_avatar.url),
                            description=generate_message_content(str(interaction.message.id)))
    await interaction.response.edit_message(embed=new_emb)


class V2SuggestionView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='👍', style=discord.ButtonStyle.primary, custom_id='upvote')
    async def upvote(self, button: discord.ui.Button, interaction: discord.Interaction):
        success, data = await perform_basic_checks(interaction)
        if not success:
            return

        client['SuggestionMessagesV2'].update_one({'MessageID': str(interaction.message.id)},
                                                  {'$push': {'Upvotes': str(interaction.user.id)}})

        await update_existing_suggestions_message(interaction)

    @discord.ui.button(label='👎', style=discord.ButtonStyle.primary, custom_id='downvote')
    async def downvote(self, button: discord.ui.Button, interaction: discord.Interaction):
        success, data = await perform_basic_checks(interaction)
        if not success:
            return

        client['SuggestionMessagesV2'].update_one({'MessageID': str(interaction.message.id)},
                                                  {'$push': {'Downvotes': str(interaction.user.id)}})

        await update_existing_suggestions_message(interaction)

    @discord.ui.button(label='See more information', style=discord.ButtonStyle.primary, custom_id='more_info')
    async def get_info(self, button: discord.ui.Button, interaction: discord.Interaction):
        data = client['SuggestionMessagesV2'].find_one({'MessageID': str(interaction.message.id)})
        if not data:
            await interaction.response.send_message('This suggestion does not exist in the database', ephemeral=True)
            return

        upvotes = data['Upvotes']
        downvotes = data['Downvotes']
        message = data['Suggestion']
        author = interaction.guild.get_member(int(data['AuthorID'])).mention
        percent = len(upvotes) / (len(upvotes) + len(downvotes)) * 100 if len(upvotes) + len(downvotes) > 0 else 0

        upvoters = [f'<@{x}>' for x in upvotes]
        if len(upvoters) == 0:
            upvoters = ['No upvoters']
        downvoters = [f'<@{x}>' for x in downvotes]
        if len(downvoters) == 0:
            downvoters = ['No downvoters']

        await interaction.response.send_message(f"""## Information about the suggestion:
{message}

**Author**: {author}
**Upvotes**: {len(upvotes)}
**Downvotes**: {len(downvotes)}
**Upvote rate**: {percent:.0f}%

**Upvoters**: {', '.join(upvoters)}
**Downvoters**: {', '.join(downvoters)}
""", ephemeral=True)


def generate_message_content(id: str):
    data = client['SuggestionMessagesV2'].find_one({'MessageID': id})
    if not data:
        raise ValueError('Message not found')

    upvotes = len(data['Upvotes'])
    downvotes = len(data['Downvotes'])
    message = data['Suggestion']

    percent = upvotes / (upvotes + downvotes) * 100 if upvotes + downvotes > 0 else 0

    return f"""{message}

**{upvotes + downvotes} votes**
**{percent:.0f}% approval**"""


class Suggestions(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        try:
            migration_1()
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return

            if client['SuggestionChannels'].count_documents({'ChannelID': str(message.channel.id)}) > 0:
                if message.channel.permissions_for(message.guild.me).manage_messages:
                    # Version 2

                    client['SuggestionMessagesV2'].insert_one({
                        'MessageID': str(message.id),
                        'Suggestion': message.content,
                        'Upvotes': [],
                        'Downvotes': [],
                        'AuthorID': str(message.author.id)
                    })

                    effective_avatar = message.author.default_avatar.url
                    if message.author.avatar:
                        effective_avatar = message.author.avatar.url

                    emb = discord.Embed(title='Suggestion', color=Color.blue(),
                                        author=discord.EmbedAuthor(
                                            name=f'{message.author.display_name}\'s suggestion',
                                            icon_url=effective_avatar),
                                        description=generate_message_content(str(message.id)))
                    new_msg = await message.channel.send(embed=emb, view=V2SuggestionView())

                    client['SuggestionMessagesV2'].update_one({'MessageID': str(message.id)},
                                                              {'$set': {'MessageID': str(new_msg.id)}})
                    await message.delete()
                else:
                    # Version 1
                    emojis = get_setting(message.guild.id, 'suggestion_emoji', '👍👎')
                    if emojis == '👍👎':
                        await message.add_reaction('👍')
                        await message.add_reaction('👎')
                    elif emojis == '✅❌':
                        await message.add_reaction('✅')
                        await message.add_reaction('❌')

                    if get_setting(message.guild.id, "suggestion_reminder_enabled", "false") == "true":
                        to_send = get_setting(message.guild.id, "suggestion_reminder_message", "")
                        sent = await message.reply(to_send)
                        await sent.delete(delay=5)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    suggestions_group = discord.SlashCommandGroup(name='suggestions', description='Suggestion commands')

    @suggestions_group.command(name='add_channel', description='Add a suggestion channel')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_add_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            if client['SuggestionChannels'].count_documents({'ChannelID': str(ctx.guild.id)}) == 0:
                client['SuggestionChannels'].insert_one({'GuildID': str(ctx.guild.id), 'ChannelID': str(channel.id)})
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'suggestions_channel_added', append_tip=True).format(
                    channel=channel.mention), ephemeral=True)
            else:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'suggestions_channel_already_exists'), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='remove_channel', description='Remove a suggestion channel')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_remove_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            if client['SuggestionChannels'].count_documents({'ChannelID': str(ctx.guild.id)}) == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "suggestions_channel_not_found"), ephemeral=True)
            else:
                client['SuggestionChannels'].delete_one({'ChannelID': str(ctx.guild.id)})
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "suggestions_channel_removed", append_tip=True).format(
                    channel=channel.mention), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='emoji', description='Choose emoji')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @discord.option(name='emoji', description='The emoji to use', choices=['👎👍', '✅❌'])
    async def cmd_choose_emoji(self, ctx: discord.ApplicationContext, emoji: str):
        try:
            set_setting(ctx.guild.id, 'suggestion_emoji', emoji)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "suggestions_emoji_set").format(emoji=emoji),
                              ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='message_reminder', description="Message reminder for people posting suggestions")
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_message_reminder(self, ctx: discord.ApplicationContext, enabled: bool, message: str):
        try:
            if len(message) < 1:
                await ctx.respond("Invalid message input.", ephemeral=True)
            set_setting(ctx.guild.id, 'suggestion_reminder_enabled', str(enabled).lower())
            set_setting(ctx.guild.id, 'suggestion_reminder_message', message)
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, 'suggestions_message_reminder_set', append_tip=True).format(
                    enabled=enabled, message=message),
                ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
