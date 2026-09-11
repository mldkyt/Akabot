import sentry_sdk
from discord import Bot, Cog, Member, Message

from utils.anti_raid import handle_mrbeast_scam, verify_member


class AntiRaid(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_member_join(self, member: Member):
        await verify_member(member)

    @Cog.listener()
    async def on_message(self, message: Message):
        try:
            if message.guild is None:
                return
            if message.author.bot:
                return
            if not message.attachments:
                return

            await handle_mrbeast_scam(message)
        except Exception as e:
            sentry_sdk.capture_exception(e)


def setup(bot: Bot):
    bot.add_cog(AntiRaid(bot))
