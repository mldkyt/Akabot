from discord import (
    Bot,
    Cog,
    Interaction,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
)
from discord.abc import GuildChannel

from utils.reaction_roles import (
    delete_by_channel,
    delete_by_messages,
    handle_interaction,
)


class ReactionRoles(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction) -> None:
        await handle_interaction(self.bot, interaction)

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        delete_by_messages([str(payload.message_id)])

    @Cog.listener()
    async def on_raw_bulk_message_delete(
        self, payload: RawBulkMessageDeleteEvent
    ) -> None:
        delete_by_messages([str(i) for i in payload.message_ids])

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        delete_by_channel(str(channel.guild.id), str(channel.id))


def setup(bot: Bot):
    bot.add_cog(ReactionRoles(bot))
