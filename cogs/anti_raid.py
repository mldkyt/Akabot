from discord import Bot, Cog, Member, Message

from logger import akabot_logger
from utils.anti_raid import (
    handle_caps,
    handle_duplicate,
    handle_emoji_flood,
    handle_flood,
    handle_invite_spam,
    handle_join_burst,
    handle_mass_mentions,
    handle_mrbeast_scam,
    handle_sticker_flood,
    verify_member,
)


class AntiRaid(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: Member):
        try:
            await verify_member(member)
            await handle_join_burst(member)
        except Exception as e:
            akabot_logger.exception(f"Failed to handle member join anti raid for {member}: {e}")

    @Cog.listener()
    async def on_message(self, message: Message):
        try:
            if message.guild is None:
                return
            if message.author.bot:
                return

            await handle_mrbeast_scam(message)
            await handle_flood(message)
            await handle_duplicate(message)
            await handle_mass_mentions(message)
            await handle_invite_spam(message)
            await handle_caps(message)
            await handle_emoji_flood(message)
            await handle_sticker_flood(message)
        except Exception as e:
            akabot_logger.exception(f"Failed to handle anti raid message {message.id}: {e}")


def setup(bot: Bot):
    bot.add_cog(AntiRaid(bot))