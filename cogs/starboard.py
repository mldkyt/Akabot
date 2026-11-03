from discord import (
    Bot,
    Cog,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    RawMessageUpdateEvent,
    RawReactionActionEvent,
    RawReactionClearEmojiEvent,
    RawReactionClearEvent,
)
from discord.abc import GuildChannel

from logger import akabot_logger
from utils.starboard import (
    handle_bulk_message_delete,
    handle_channel_delete,
    handle_message_delete,
    handle_message_edit,
    handle_reaction_event,
    sync_all_bot_permissions,
)


class Starboard(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_ready(self) -> None:
        try:
            await sync_all_bot_permissions(self.bot)
        except Exception as e:
            akabot_logger.exception(
                f"Failed to sync starboard bot permissions: {e}"
            )

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        try:
            await handle_reaction_event(self.bot, payload, payload.emoji)
        except Exception as e:
            akabot_logger.exception(f"Failed to handle starboard reaction add: {e}")

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent) -> None:
        try:
            await handle_reaction_event(self.bot, payload, payload.emoji)
        except Exception as e:
            akabot_logger.exception(f"Failed to handle starboard reaction remove: {e}")

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload: RawReactionClearEvent) -> None:
        try:
            await handle_reaction_event(self.bot, payload)
        except Exception as e:
            akabot_logger.exception(f"Failed to handle starboard reaction clear: {e}")

    @Cog.listener()
    async def on_raw_reaction_clear_emoji(
        self, payload: RawReactionClearEmojiEvent
    ) -> None:
        try:
            await handle_reaction_event(self.bot, payload, payload.emoji)
        except Exception as e:
            akabot_logger.exception(
                f"Failed to handle starboard reaction clear emoji: {e}"
            )

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        if payload.guild_id is None:
            return

        try:
            await handle_message_delete(
                self.bot, payload.guild_id, payload.message_id
            )
        except Exception as e:
            akabot_logger.exception(f"Failed to handle starboard message delete: {e}")

    @Cog.listener()
    async def on_raw_bulk_message_delete(
        self, payload: RawBulkMessageDeleteEvent
    ) -> None:
        if payload.guild_id is None:
            return

        try:
            await handle_bulk_message_delete(
                self.bot, payload.guild_id, list(payload.message_ids)
            )
        except Exception as e:
            akabot_logger.exception(
                f"Failed to handle starboard bulk message delete: {e}"
            )

    @Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent) -> None:
        if payload.guild_id is None:
            return

        try:
            await handle_message_edit(
                self.bot, payload.guild_id, payload.message_id
            )
        except Exception as e:
            akabot_logger.exception(f"Failed to handle starboard message edit: {e}")

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        try:
            await handle_channel_delete(
                self.bot, channel.guild.id, channel.id
            )
        except Exception as e:
            akabot_logger.exception(
                f"Failed to handle starboard channel delete: {e}"
            )


def setup(bot: Bot):
    if not bot.intents.message_content:
        akabot_logger.warning(
            "Starboards: message content intent is disabled. Starboard posts "
            "will be created without message text."
        )

    bot.add_cog(Starboard(bot))
