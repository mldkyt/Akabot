from discord import ButtonStyle, Color, Embed, EmbedFooter, Interaction, Message
from discord.ui import Button, View, button
from sqlalchemy import insert, select

from database import engine, suggestion_voting, suggestions
from utils.server_settings import ServerSetting, SettingType

suggestion_channels = ServerSetting(
    name="Suggestion channels", setting_type=SettingType.LIST
)

suggestion_threads = ServerSetting(
    name="Suggestion threads", setting_type=SettingType.NORMAL
)


def make_embed(message_id: int, content: str | Embed) -> Embed:
    if isinstance(content, Embed):
        content = str(content.description)

    upvotes = 0
    downvotes = 0

    with engine.begin() as c:
        suggestion_data = c.execute(
            select(suggestion_voting.c.vote).where(
                suggestion_voting.c.message_id == str(message_id)
            )
        ).fetchall()

    for i in suggestion_data:
        if i[0] == 1:
            upvotes += 1
        if i[0] == 0:
            downvotes += 1

    return Embed(
        title="Suggestion",
        description=content,
        color=Color.blurple(),
        footer=EmbedFooter(f"{upvotes} upvotes, {downvotes} downvotes"),
    )


class VotingOptions(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Upvote", custom_id="suggestion_upvote", style=ButtonStyle.secondary)
    async def upvote(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            data_suggestion = c.execute(
                select(suggestions.c.author_id).where(
                    suggestions.c.message_id == str(interaction.message.id)
                )
            ).fetchone()

            if not data_suggestion:
                await interaction.respond(
                    "Suggestion doesn't exist in DB!", ephemeral=True
                )
                return

            if data_suggestion[0] == str(interaction.user.id):
                await interaction.respond(
                    "You can't vote for your own suggestion!", ephemeral=True
                )
                return

            if c.execute(
                select(suggestion_voting.c.vote).where(
                    (suggestion_voting.c.message_id == str(interaction.message.id))
                    & (suggestion_voting.c.member_id == str(interaction.user.id))
                )
            ).fetchone():
                await interaction.respond("Already voted!", ephemeral=True)
                return

            c.execute(
                insert(suggestion_voting).values(
                    message_id=str(interaction.message.id),
                    member_id=str(interaction.user.id),
                    vote=1,
                )
            )

        await interaction.edit(
            embed=make_embed(interaction.message.id, interaction.message.embeds[0])
        )

    @button(
        label="Downvote", custom_id="suggestion_downvote", style=ButtonStyle.secondary
    )
    async def downvote(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            data_suggestion = c.execute(
                select(suggestions.c.author_id).where(
                    suggestions.c.message_id == str(interaction.message.id)
                )
            ).fetchone()

            if not data_suggestion:
                await interaction.respond(
                    "Suggestion doesn't exist in DB!", ephemeral=True
                )
                return

            if data_suggestion[0] == str(interaction.user.id):
                await interaction.respond(
                    "You can't vote for your own suggestion!", ephemeral=True
                )
                return

            if c.execute(
                select(suggestion_voting.c.vote).where(
                    (suggestion_voting.c.message_id == str(interaction.message.id))
                    & (suggestion_voting.c.member_id == str(interaction.user.id))
                )
            ).fetchone():
                await interaction.respond("Already voted!", ephemeral=True)
                return

            c.execute(
                insert(suggestion_voting).values(
                    message_id=str(interaction.message.id),
                    member_id=str(interaction.user.id),
                    vote=0,
                )
            )

        await interaction.edit(
            embed=make_embed(interaction.message.id, interaction.message.embeds[0])
        )

    @button(
        label="Information",
        custom_id="suggestion_information",
        style=ButtonStyle.primary,
    )
    async def information(self, button: Button, interaction: Interaction):
        with engine.begin() as c:
            data_suggestion = c.execute(
                select(suggestions.c.author_id).where(
                    suggestions.c.message_id == str(interaction.message.id)
                )
            ).fetchone()

            if not data_suggestion:
                await interaction.respond(
                    "Failed to fetch suggestion data!", ephemeral=True
                )
                return

            upvotes = c.execute(
                select(suggestion_voting.c.member_id)
                .where(
                    (suggestion_voting.c.message_id == str(interaction.message.id))
                    & (suggestion_voting.c.vote == 1)
                )
                .limit(10)
            ).fetchall()

            downvotes = c.execute(
                select(suggestion_voting.c.member_id)
                .where(
                    (suggestion_voting.c.message_id == str(interaction.message.id))
                    & (suggestion_voting.c.vote == 0)
                )
                .limit(10)
            ).fetchall()

        upvotes_str = ", ".join(f"<@{i[0]}>" for i in upvotes)
        downvotes_str = ", ".join(f"<@{i[0]}>" for i in downvotes)
        message = f"""# Suggestion information

**Author**: <@{data_suggestion[0]}>

**Upvotes**: {upvotes_str}
**Downvotes**: {downvotes_str}"""

        await interaction.respond(message, ephemeral=True)


async def handle_suggestion_message(msg: Message):
    # Check if channel is suggestion channel
    with engine.begin() as c:
        if str(msg.channel.id) not in suggestion_channels.get(c, msg.guild.id):
            return

        await msg.delete()
        sent_message = await msg.channel.send(
            embed=make_embed(0, msg.content), view=VotingOptions()
        )

        with engine.begin() as c:
            c.execute(
                insert(suggestions).values(
                    author_id=str(msg.author.id), message_id=str(sent_message.id)
                )
            )

            do_suggestion_theads = suggestion_threads.get(c, msg.guild.id) == "true"

        if do_suggestion_theads:
            await sent_message.create_thread(name=f"Thread: {msg.content[:15]}")
